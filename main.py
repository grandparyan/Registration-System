import os
import json
import gspread
import logging
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS # 啟用 CORS 讓網頁可以跨域呼叫
from oauth2client.service_account import ServiceAccountCredentials

# 設定日誌等級，方便在 Render 上除錯
logging.basicConfig(level=logging.INFO)
# ----------------------------------------------------
# 這是您的 Google Sheets 試算表 ID
# 請確保您的服務帳號有此試算表的「編輯者」權限
spreadsheet_id = "1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4"
WORKSHEET_NAME = "設備報修" # 這是您的程式碼不斷報錯的地方，請檢查是否完全匹配

# Google Sheets API 範圍
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 全域變數用於儲存 gspread client 和工作表
client = None
sheet = None

def initialize_gspread():
    """初始化 Google Sheets 連線，確保服務啟動時只執行一次。"""
    global client, sheet
    
    if client:
        return True # 已初始化

    try:
        creds_json = os.environ.get('SERVICE_ACCOUNT_CREDENTIALS')
        if not creds_json:
            logging.error("致命錯誤：找不到 SERVICE_ACCOUNT_CREDENTIALS 環境變數。")
            return False

        # 嘗試解析 JSON 憑證
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            scope
        )
        client = gspread.authorize(creds)
        
        # 嘗試打開試算表並選取工作表
        sheet = client.open_by_key(spreadsheet_id).worksheet(WORKSHEET_NAME)
        logging.info(f"成功連線到 Google Sheets。工作表名稱: {WORKSHEET_NAME}")
        return True

    except gspread.exceptions.WorksheetNotFound:
        # 這是您目前遇到的錯誤，請再次檢查 Sheets 上的名稱是否完全是「設備報修」
        logging.error(f"嚴重錯誤：找不到名稱為「{WORKSHEET_NAME}」的工作表。請檢查名稱或試算表 ID。")
        return False
    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"嚴重錯誤：找不到試算表ID為「{spreadsheet_id}」的試算表。請檢查 ID 或服務帳號權限。")
        return False
    except Exception as e:
        logging.error(f"連線到 Google Sheets 時發生未知錯誤: {e}")
        return False

# ----------------------------------------------------
# Flask 應用程式設定
app = Flask(__name__)
# 啟用 CORS，允許所有來源的網頁呼叫您的 API
CORS(app) 

# 在應用程式第一次請求前先初始化 gspread
with app.app_context():
    initialize_gspread()

# 定義接收網頁資料的 API 端點
# 注意：前端的請求路徑必須是 /submit_report
@app.route('/submit_report', methods=['POST'])
def submit_data_api():
    """
    接收來自網頁的 POST 請求，將 JSON 資料寫入 Google Sheets。
    """
    if not sheet:
        # 如果初始化失敗，回傳伺服器錯誤（通常是因為找不到工作表或權限不足）
        return jsonify({"status": "error", "message": "伺服器初始化失敗，無法連線至 Google Sheets。請檢查 log 訊息。"}), 500

    # 嘗試取得 JSON 資料
    try:
        data = request.get_json()
    except Exception:
        logging.error("請求資料解析失敗：不是有效的 JSON 格式。")
        return jsonify({"status": "error", "message": "請求必須是 JSON 格式。請檢查網頁前端的 Content-Type。"}), 400

    if not data:
        logging.error("請求資料為空。")
        return jsonify({"status": "error", "message": "請求資料為空。"}), 400
    
    try:
        # 從 JSON 資料中提取欄位
        reporterName = data.get('reporterName', 'N/A')
        deviceLocation = data.get('deviceLocation', 'N/A')
        problemDescription = data.get('problemDescription', 'N/A')
        helperTeacher = data.get('helperTeacher', '無指定')

        # 檢查關鍵欄位是否存在
        if not all([reporterName != 'N/A', deviceLocation != 'N/A', problemDescription != 'N/A']):
            logging.error(f"缺少必要資料: {data}")
            return jsonify({"status": "error", "message": "缺少必要的報修資料（如報修人、地點或描述）。"}), 400

        # 加入當前時間欄位
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            timestamp, 
            str(reporterName),
            str(deviceLocation),
            str(problemDescription),
            str(helperTeacher),
            "待處理" 
        ]
        
        # 將資料附加到工作表的最後一行
        sheet.append_row(row)
        
        logging.info(f"資料成功寫入：{row}")
        return jsonify({"status": "success", "message": "設備報修資料已成功送出！"}), 200
        
    except Exception as e:
        logging.error(f"寫入 Google Sheets 時發生錯誤: {e}")
        return jsonify({"status": "error", "message": f"提交失敗：{str(e)}，可能是 Sheets API 限制或連線問題。"}), 500

# ----------------------------------------------------
# 預設首頁（可選，用於健康檢查或基本訊息）
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "報修 API 服務運行中。請使用 POST 請求到 /submit_report 提交資料。",
        "sheets_status": "連線成功" if sheet else "連線失敗"
    })

if __name__ == '__main__':
    # 僅供本地測試使用
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
