import os
import gspread
from flask import Flask, jsonify
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# 使用 os.environ 讀取環境變數，確保程式碼可以在 Render 上運作
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
if not GOOGLE_SERVICE_ACCOUNT_CREDENTIALS:
    raise ValueError("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set.")

try:
    # 設置 Google 憑證
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(
        eval(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS), # 使用 eval 來解析 JSON 字串
        scopes=scopes
    )
    client = gspread.authorize(creds)
    
    # 替換成您的 Google 試算表名稱或 ID
    SPREADSHEET_NAME = "您的試算表名稱"
    spreadsheet = client.open(SPREADSHEET_NAME)
    
    # 讀取試算表中的所有資料
    worksheet = spreadsheet.get_worksheet(0)
    data = worksheet.get_all_records()

    print("成功連線到 Google 試算表！")
    print(f"試算表 '{SPREADSHEET_NAME}' 的資料為：")
    print(data)

except Exception as e:
    print(f"連線到 Google 試算表時發生錯誤：{e}")

@app.route('/')
def home():
    if not data:
        return "資料讀取失敗或試算表為空！"
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
