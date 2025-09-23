import os
import json
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from gspread import service_account
from json.decoder import JSONDecodeError
from datetime import datetime

app = Flask(__name__)

# 使用 os.environ 讀取環境變數，確保程式碼可以在 Render 上運作
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
# 從環境變數讀取試算表名稱，若無則使用預設值
SPREADSHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME', '設備報修')

def get_service_account_credentials():
    """安全地解析 JSON 憑證字串並返回憑證對象。"""
    if not GOOGLE_SERVICE_ACCOUNT_CREDENTIALS:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set.")
    
    try:
        # 嘗試解析 JSON 內容
        creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS)
        return creds_info
    except JSONDecodeError as e:
        print(f"嘗試解析的 JSON 憑證內容：{GOOGLE_SERVICE_ACCOUNT_CREDENTIALS}")
        raise ValueError(f"無法解析 JSON 憑證。請確認內容正確無誤。錯誤訊息: {e}")
    except Exception as e:
        print(f"憑證解析時發生未知錯誤，但 JSON 內容可能正確。錯誤訊息：{e}")
        raise ValueError(f"憑證解析時發生未知錯誤：{e}")

# 初始化 Google 憑證
try:
    creds_info = get_service_account_credentials()
    try:
        # 嘗試使用新版 gspread 的參數
        gc = service_account(credentials=creds_info)
    except TypeError:
        # 如果失敗，改用舊版 gspread 的參數
        gc = service_account(json_info=creds_info)
    
    spreadsheet = gc.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.get_worksheet(0)  # 取得第一個工作表
    print("成功連線到 Google 試算表！")
except Exception as e:
    print(f"連線到 Google 試算表時發生錯誤：{e}")
    worksheet = None # 如果連線失敗，將 worksheet 設為 None

@app.route('/')
def home():
    """顯示報修表單網頁。"""
    records = []
    if worksheet:
        try:
            # 取得標題列
            headers = worksheet.row_values(1)
            # 取得所有資料列
            all_values = worksheet.get_all_values()
            
            # 從第二列開始讀取資料並轉換為字典列表
            if len(all_values) > 1:
                data_rows = all_values[1:]
                for row in data_rows:
                    record = dict(zip(headers, row))
                    records.append(record)

        except Exception as e:
            print(f"讀取試算表資料時發生錯誤: {e}")
            
    # 讀取 index.html 檔案內容並使用 Jinja2 傳遞資料
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return render_template_string(html_content, records=records)

@app.route('/submit_request', methods=['POST'])
def submit_request():
    """接收表單資料並寫入 Google 試算表。"""
    if worksheet is None:
        return jsonify({'success': False, 'message': '後端連線到試算表失敗。'})

    try:
        # 取得表單欄位的值
        reporter_name = request.form.get('reporter_name')
        location = request.form.get('location')
        problem_description = request.form.get('problem_description')
        teacher = request.form.get('teacher')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 建立一個新的資料列，順序需與 Google 試算表欄位順序一致
        new_row = [reporter_name, location, problem_description, teacher, timestamp]
        
        # 將資料附加到工作表的最後一行
        worksheet.append_row(new_row)
        
        print(f"成功將資料寫入試算表：{new_row}")
        # 提交成功後，重新導向回首頁以顯示更新後的清單
        return redirect(url_for('home'))

    except Exception as e:
        print(f"寫入試算表時發生錯誤：{e}")
        # 如果失敗，返回一個錯誤頁面或訊息
        return f"提交失敗，請再試一次。錯誤：{e}"

# 注意：你提供的 HTML 中使用了 confirm() 函式，這在部分瀏覽器或環境下可能會有問題。
# 在 Canvas 預覽中，這類彈出視窗不會顯示，建議改用自訂的模態視窗來提供更好的使用者體驗。
# 此外，'edit_request' 和 'delete_request' 路由尚未實作，如果你需要這些功能，我們可以再討論如何添加。

if __name__ == '__main__':
    # 為了方便本地測試，設定 host 為 '0.0.0.0'
    app.run(debug=True, host='0.0.0.0')
