# 程式碼說明：
# 1. 初始化 Flask 應用程式。
# 2. 透過 gspread 函式庫連線到 Google 試算表。
# 3. 定義不同的路由 (routes) 來處理網頁請求。
# 4. 實作 CRUD (建立、讀取、更新、刪除) 功能。

from flask import Flask, render_template, request, redirect, url_for
import gspread
import json
import os
from datetime import datetime

# 初始化 Flask 應用程式
app = Flask(__name__, template_folder='templates')

def get_worksheet():
    """連線到 Google 試算表並返回工作表物件。"""
    try:
        # 嘗試從 Render 環境變數讀取憑證內容
        credentials_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
        if credentials_json:
            # 從環境變數中的 JSON 字串建立憑證
            credentials = json.loads(credentials_json)
            gc = gspread.service_account_from_dict(credentials)
        else:
            # 如果在 Render 上找不到，則嘗試從本地檔案讀取 (用於本地開發)
            if os.path.exists('credentials.json'):
                gc = gspread.service_account(filename='credentials.json')
            else:
                # 如果兩者都找不到，則拋出錯誤
                raise FileNotFoundError("錯誤：找不到 'credentials.json' 檔案或 'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS' 環境變數。請依照 README.md 說明進行設定。")

        # 讀取試算表名稱，優先使用環境變數
        spreadsheet_name = os.environ.get('GOOGLE_SHEET_NAME', '設備報修紀錄')
        
        # 開啟試算表並選擇第一個工作表
        sh = gc.open(spreadsheet_name)
        return sh.sheet1
    except Exception as e:
        # 在部署時，如果發生錯誤，印出詳細資訊方便除錯
        print(f"連線到 Google 試算表時發生錯誤：{e}")
        # 在網頁上顯示錯誤訊息
        return f"讀取資料時發生錯誤：{e}", 500

@app.route('/')
def index():
    """顯示主頁面，包含報修表單和所有報修紀錄。"""
    try:
        worksheet_result = get_worksheet()
        # 檢查回傳值是否為 tuple (代表錯誤)
        if isinstance(worksheet_result, tuple):
            return worksheet_result
        
        records = worksheet_result.get_all_records()
        return render_template('index.html', records=records)
    except Exception as e:
        return f"讀取資料時發生錯誤：{e}", 500

@app.route('/submit_request', methods=['POST'])
def submit_request():
    """處理表單提交，將新紀錄寫入 Google 試算表。"""
    try:
        worksheet_result = get_worksheet()
        if isinstance(worksheet_result, tuple):
            return worksheet_result
            
        reporter_name = request.form['reporter_name']
        location = request.form['location']
        problem_description = request.form['problem_description']
        teacher = request.form['teacher']
        
        # 自動產生報修時間
        request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 新增一列資料
        worksheet_result.append_row([reporter_name, location, problem_description, teacher, request_time])
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"提交資料時發生錯誤：{e}", 500

@app.route('/edit/<int:row_index>', methods=['GET', 'POST'])
def edit_request(row_index):
    """
    處理報修紀錄的編輯：
    - GET 請求：顯示編輯表單，並填入現有資料。
    - POST 請求：更新試算表中的資料。
    """
    try:
        worksheet_result = get_worksheet()
        if isinstance(worksheet_result, tuple):
            return worksheet_result
            
        # 因為 get_all_records() 不包含標題列，所以實際列號要 +2 (標題列 + 0-based index)
        sheet_row_index = row_index + 1
        
        if request.method == 'POST':
            # 從表單取得更新後的資料
            updated_data = [
                request.form['reporter_name'],
                request.form['location'],
                request.form['problem_description'],
                request.form['teacher'],
                request.form['request_time']
            ]
            
            # 更新試算表中的該列資料
            worksheet_result.update(f'A{sheet_row_index}:E{sheet_row_index}', [updated_data])
            return redirect(url_for('index'))
        else:
            # 取得該列資料，用來填入編輯表單
            record = worksheet_result.row_values(sheet_row_index)
            # 檢查是否讀取到資料
            if not record:
                 return "找不到該筆報修紀錄！", 404
            
            return render_template('edit.html', record=record, row_index=row_index)

    except Exception as e:
        return f"處理編輯請求時發生錯誤：{e}", 500

@app.route('/delete/<int:row_index>')
def delete_request(row_index):
    """處理刪除請求，從試算表中刪除指定的列。"""
    try:
        worksheet_result = get_worksheet()
        if isinstance(worksheet_result, tuple):
            return worksheet_result
            
        # 因為 get_all_records() 不包含標題列，所以實際列號要 +2 (標題列 + 0-based index)
        sheet_row_index = row_index + 1
        worksheet_result.delete_rows(sheet_row_index)
        return redirect(url_for('index'))
    except Exception as e:
        return f"刪除資料時發生錯誤：{e}", 500

if __name__ == '__main__':
    # 這裡的程式碼只在本地執行時會被呼叫
    # 在 Render 上會由 gunicorn 伺服器啟動
    app.run(debug=True)
