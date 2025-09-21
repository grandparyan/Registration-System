import os
import gspread
import json
from flask import Flask, jsonify
from google.oauth2.service_account import Credentials
from json.decoder import JSONDecodeError

app = Flask(__name__)

# 使用 os.environ 讀取環境變數，確保程式碼可以在 Render 上運作
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')

# 初始化 data 變數
data = []

def get_credentials():
    """安全地解析 JSON 憑證字串並返回憑證對象。"""
    if not GOOGLE_SERVICE_ACCOUNT_CREDENTIALS:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set.")
    
    try:
        # 嘗試解析 JSON 內容
        creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS)
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(
            creds_info, 
            scopes=scopes
        )
        return creds
    except JSONDecodeError as e:
        # 如果 JSON 解析失敗，拋出更清晰的錯誤訊息
        raise ValueError(f"無法解析 JSON 憑證。請確認內容正確無誤。錯誤訊息: {e}")
    except Exception as e:
        # 捕捉其他可能的錯誤
        raise ValueError(f"憑證解析時發生未知錯誤：{e}")

try:
    # 設置 Google 憑證
    creds = get_credentials()
    client = gspread.authorize(creds)
    
    # 替換成您的 Google 試算表名稱或 ID
    SPREADSHEET_NAME = "設備報修"
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
