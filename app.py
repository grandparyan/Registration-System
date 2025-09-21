# 程式碼說明：
# 1. 初始化 Flask 應用程式。
# 2. 透過 gspread 函式庫連線到 Google 試算表。
# 3. 定義不同的路由 (routes) 來處理網頁請求。
# 4. 實作 CRUD (建立、讀取、更新、刪除) 功能。

from flask import Flask, render_template, request, redirect, url_for
import gspread
import os
from datetime import datetime

# 檢查 credentials.json 檔案是否存在
if not os.path.exists('credentials.json'):
    print("錯誤：找不到 'credentials.json' 檔案。")
    print("請依照 README.md 說明，從 Google Cloud Console 下載服務帳號金鑰檔案，並重新命名為 'credentials.json'。")
    exit()

# 啟用 Google 試算表 API
try:
    gc = gspread.service_account(filename='credentials.json')
    # 請將下方 '你的試算表名稱' 換成您自己的 Google 試算表名稱
    spreadsheet_name = "設備報修紀錄"
    sh = gc.open(spreadsheet_name)
    worksheet = sh.sheet1
except Exception as e:
    print(f"連線到 Google 試算表時發生錯誤：{e}")
    print("請確認以下事項：")
    print("- 您的 'credentials.json' 檔案是否正確。")
    print("- Google Sheets API 是否已在您的 Google Cloud 專案中啟用。")
    print("- 您是否已將試算表分享給服務帳號的電子郵件地址。")
    exit()

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    """顯示主頁面，包含報修表單和所有報修紀錄。"""
    try:
        # 讀取所有報修紀錄
        records = worksheet.get_all_records()
        return render_template('index.html', records=records)
    except Exception as e:
        return f"讀取資料時發生錯誤：{e}"

@app.route('/submit_request', methods=['POST'])
def submit_request():
    """處理表單提交，將新紀錄寫入 Google 試算表。"""
    try:
        reporter_name = request.form['reporter_name']
        location = request.form['location']
        problem_description = request.form['problem_description']
        teacher = request.form['teacher']
        
        # 自動產生報修時間
        request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 新增一列資料
        worksheet.append_row([reporter_name, location, problem_description, teacher, request_time])
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"提交資料時發生錯誤：{e}"

@app.route('/edit/<int:row_index>', methods=['GET', 'POST'])
def edit_request(row_index):
    """
    處理報修紀錄的編輯：
    - GET 請求：顯示編輯表單，並填入現有資料。
    - POST 請求：更新試算表中的資料。
    """
    try:
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
            worksheet.update(f'A{sheet_row_index}:E{sheet_row_index}', [updated_data])
            return redirect(url_for('index'))
        else:
            # 取得該列資料，用來填入編輯表單
            record = worksheet.row_values(sheet_row_index)
            # 檢查是否讀取到資料
            if not record:
                 return "找不到該筆報修紀錄！", 404
            
            return render_template('edit.html', record=record, row_index=row_index)

    except Exception as e:
        return f"處理編輯請求時發生錯誤：{e}"

@app.route('/delete/<int:row_index>')
def delete_request(row_index):
    """處理刪除請求，從試算表中刪除指定的列。"""
    try:
        # 因為 get_all_records() 不包含標題列，所以實際列號要 +2 (標題列 + 0-based index)
        sheet_row_index = row_index + 1
        worksheet.delete_rows(sheet_row_index)
        return redirect(url_for('index'))
    except Exception as e:
        return f"刪除資料時發生錯誤：{e}"

if __name__ == '__main__':
    app.run(debug=True)
