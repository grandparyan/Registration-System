import os
import datetime
from flask import Flask, render_template, request, jsonify
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 初始化 Flask 應用程式
app = Flask(__name__)

# --- Google Sheets API 設定 ---
# 請將您的服務帳號 JSON 檔案放在與 main.py 相同的資料夾中，並命名為 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def get_sheets_service():
    """建立並回傳 Google Sheets API 服務物件。"""
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"Error initializing Google Sheets API: {e}")
        return None

# --- Web 應用程式路由 ---
@app.route('/')
def index():
    """根路由，用於顯示報修表單網頁。"""
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_form():
    """處理表單提交的路由。"""
    data = request.json
    
    reporterName = data.get('reporterName', '')
    deviceLocation = data.get('deviceLocation', '')
    problemDescription = data.get('problemDescription', '')
    helperTeacher = data.get('helperTeacher', '')
    repairTime = str(datetime.datetime.now())
    
    # 檢查是否有缺少任何欄位
    if not all([reporterName, deviceLocation, problemDescription, helperTeacher]):
        return jsonify({"message": "錯誤：所有欄位皆為必填。"}), 400

    # Google 試算表 ID
    SPREADSHEET_ID = '1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4'
    SHEET_NAME = '設備報修'
    
    try:
        service = get_sheets_service()
        if not service:
            raise Exception("無法初始化 Google Sheets API 服務。")

        sheet = service.spreadsheets()
        
        # 準備要寫入試算表的資料
        row_data = [repairTime, reporterName, deviceLocation, problemDescription, helperTeacher, '待處理']
        
        # 將資料附加到工作表中
        body = {
            'values': [row_data]
        }
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=SHEET_NAME,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return jsonify({"message": "報修已送出！"}), 200

    except Exception as e:
        print(f"Error appending data to Google Sheet: {e}")
        return jsonify({"message": f"送出失敗，請重試。錯誤訊息：{e}"}), 500

if __name__ == '__main__':
    # 在本機執行 Web 伺服器
    app.run(debug=True)
