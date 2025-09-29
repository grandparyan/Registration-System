import os
import json
import gspread
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS # 新增：導入 CORS
from oauth2client.service_account import ServiceAccountCredentials

# 設定日誌等級，方便在 Render 上除錯
logging.basicConfig(level=logging.INFO)

# --- Google Sheets 連線與初始化 ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 全域變數用於儲存 gspread client 和工作表
client = None
sheet = None
spreadsheet_id = "1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4" # 您的試算表 ID

def initialize_gspread():
    """初始化 Google Sheets 連線，確保服務啟動時只執行一次。"""
    global client, sheet
    
    if client:
        # 如果已經初始化，則直接返回
        return True

    try:
        creds_json = os.environ.get('SERVICE_ACCOUNT_CREDENTIALS')
        if not creds_json:
            logging.error("錯誤：找不到 SERVICE_ACCOUNT_CREDENTIALS 環境變數。")
            return False

        # 嘗試解析 JSON 憑證
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            scope
        )
        client = gspread.authorize(creds)
        
        # 打開試算表並選取工作表
        sheet = client.open_by_key(spreadsheet_id).worksheet("設備報修")
        logging.info("成功連線到 Google Sheets。")
        return True

    except json.JSONDecodeError as e:
        logging.error(f"錯誤：無法解析 SERVICE_ACCOUNT_CREDENTIALS 環境變數為 JSON。詳細錯誤: {e}")
        return False
    except gspread.exceptions.WorksheetNotFound:
        logging.error("錯誤：找不到名稱為「設備報修」的工作表。")
        return False
    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"錯誤：找不到試算表ID為「{spreadsheet_id}」的試算表。請檢查權限。")
        return False
    except Exception as e:
        logging.error(f"連線到 Google Sheets 時發生未知錯誤: {e}")
        return False

# --- Flask 應用程式設定 ---
app = Flask(__name__)
CORS(app) # 新增：啟用 CORS，允許跨域請求

# 在應用程式第一次請求前先初始化 gspread
with app.app_context():
    initialize_gspread()

# 定義接收網頁資料的 API 端點
@app.route('/submit_report', methods=['POST'])
def submit_data_api():
    """
    接收來自網頁的 POST 請求，將 JSON 資料寫入 Google Sheets。
    """
    if not sheet:
        # 如果初始化失敗，回傳伺服器錯誤
        return jsonify({"status": "error", "message": "伺服器初始化失敗，無法連線至 Google Sheets。"}), 500

    # 確保接收到的資料是 JSON 格式
    data = request.get_json()
    if not data:
        # 如果 request.get_json() 失敗，表示前端沒有正確發送 JSON 格式
        logging.error("請求資料不是有效的 JSON 格式或 Content-Type 設定錯誤。")
        return jsonify({"status": "error", "message": "請求必須是 JSON 格式。請檢查網頁前端的 Content-Type。"}), 400
    
    try:
        # 從 JSON 資料中提取欄位
        reporterName = data.get('reporterName')
        deviceLocation = data.get('deviceLocation')
        problemDescription = data.get('problemDescription')
        helperTeacher = data.get('helperTeacher')

        # 檢查關鍵欄位是否存在
        if not all([reporterName, deviceLocation, problemDescription]):
            return jsonify({"status": "error", "message": "缺少必要的報修資料（如報修人、地點或描述）。"}), 400

        # 您可以加入當前時間欄位
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            timestamp, # 第一個欄位，記錄時間
            str(reporterName),
            str(deviceLocation),
            str(problemDescription),
            str(helperTeacher or "無指定"), # 處理選填欄位
            "待處理" # 預設狀態
        ]
        
        # 將資料附加到工作表的最後一行
        sheet.append_row(row)
        
        logging.info(f"資料成功寫入：{row}")
        return jsonify({"status": "success", "message": "設備報修資料已成功送出！"}), 200
        
    except Exception as e:
        logging.error(f"提交資料時發生錯誤: {e}")
        return jsonify({"status": "error", "message": f"提交失敗：{str(e)}"}), 500

# 這部分是給本地開發測試使用，Render 部署時會使用 Gunicorn 或其他 WSGI Server
if __name__ == '__main__':
    # 注意：在 Render 上，您不需要使用 app.run()，請參閱下方的部署說明。
    print("在 http://127.0.0.1:5000/submit_report 測試 POST 請求...")
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
