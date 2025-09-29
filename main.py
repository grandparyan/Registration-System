import os
import json
import gspread
import logging
import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS 
from oauth2client.service_account import ServiceAccountCredentials

# 設定日誌等級，方便在 Render 上除錯
logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------
# 設定 Google Sheets 參數
# 請確保您的服務帳號有此試算表的「編輯者」權限
spreadsheet_id = "1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4"
WORKSHEET_NAME = "設備報修" # 請再次檢查此名稱是否與您的 Google Sheets 工作表名稱完全匹配

# Google Sheets API 範圍
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 全域變數用於儲存 gspread client 和工作表
client = None
sheet = None

def initialize_gspread():
    """初始化 Google Sheets 連線。"""
    global client, sheet
    
    # 避免重複初始化
    if client:
        return True 

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
    # 確保應用程式啟動時就嘗試連線
    initialize_gspread()

# ----------------------------------------------------
# 路由定義

# 1. 根路由：用於顯示 HTML 報修表單
@app.route('/')
def home():
    """
    回傳完整的 HTML 報修表單內容，作為服務的前端。
    """
    # 將您的 repair_form.html 內容作為字串回傳
    html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>設備報修系統</title>
    <!-- 載入 Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* 使用 Inter 字體以確保跨平台一致性 */
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f4f7f9;
        }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">

    <div class="w-full max-w-lg bg-white p-8 md:p-10 rounded-xl shadow-2xl">
        
        <!-- 標題區塊 -->
        <div class="text-center mb-8">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-indigo-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37a1.724 1.724 0 002.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <h1 class="text-3xl font-bold text-gray-900">設備報修單</h1>
            <p class="text-gray-500 mt-1">請填寫詳細資訊，以便我們快速處理。</p>
        </div>

        <!-- 訊息顯示區塊 (取代 alert) -->
        <div id="message-box" class="hidden mb-6 p-3 text-center rounded-lg font-medium transition-all duration-300"></div>

        <!-- 表單開始 -->
        <form id="repairForm" class="space-y-6">
            
            <!-- 報修人姓名 (reporterName) -->
            <div>
                <label for="reporter_name_input" class="block text-sm font-medium text-gray-700 mb-1">報修人姓名 (必填)</label>
                <input type="text" id="reporter_name_input" required class="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500">
            </div>

            <!-- 設備位置 (deviceLocation) -->
            <div>
                <label for="location_input" class="block text-sm font-medium text-gray-700 mb-1">設備位置 / 教室名稱 (必填)</label>
                <input type="text" id="location_input" required class="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500">
            </div>

            <!-- 問題描述 (problemDescription) -->
            <div>
                <label for="problem_input" class="block text-sm font-medium text-gray-700 mb-1">問題詳細描述 (必填)</label>
                <textarea id="problem_input" rows="4" required class="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 resize-none"></textarea>
            </div>

            <!-- 協辦老師 (helperTeacher) 欄位已移除 -->
            <!-- 舊的協辦老師選擇欄位已被移除 -->

            <!-- 提交按鈕 -->
            <div>
                <button type="submit" id="submit-button" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out">
                    送出報修單
                </button>
            </div>
        </form>
        <!-- 表單結束 -->
    </div>

    <script>
        // 設定您的 Render API 網址，這是最關鍵的連接點
        // 請確保您的 Render 服務已成功啟動並連線到 Sheets！
        const API_URL = "https://registration-system-ru2g.onrender.com/submit_report";

        const form = document.getElementById('repairForm');
        const submitButton = document.getElementById('submit-button');
        const messageBox = document.getElementById('message-box');

        // 顯示訊息函式（取代 alert）
        function showMessage(message, isSuccess) {
            messageBox.textContent = message;
            messageBox.classList.remove('hidden', 'bg-red-100', 'text-red-800', 'bg-green-100', 'text-green-800');
            
            if (isSuccess) {
                messageBox.classList.add('bg-green-100', 'text-green-800');
            } else {
                messageBox.classList.add('bg-red-100', 'text-red-800');
            }
            // 5 秒後隱藏訊息
            setTimeout(() => {
                messageBox.classList.add('hidden');
            }, 5000);
        }

        form.addEventListener('submit', async function(event) {
            // 阻止表單的預設提交行為
            event.preventDefault();

            // 鎖定按鈕並顯示載入狀態
            submitButton.disabled = true;
            submitButton.textContent = '正在送出...';
            submitButton.classList.add('opacity-50', 'cursor-not-allowed');

            try {
                // 1. 從表單中收集資料，確保 Key Names 與 Python 後端完全匹配
                // 注意：helperTeacher 欄位已移除
                const reportData = {
                    "reporterName": document.getElementById('reporter_name_input').value,
                    "deviceLocation": document.getElementById('location_input').value,
                    "problemDescription": document.getElementById('problem_input').value,
                };

                // 2. 發送 POST 請求
                const response = await fetch(API_URL, {
                    method: 'POST',
                    // 告知伺服器我們正在傳送 JSON 格式的資料
                    headers: {
                        'Content-Type': 'application/json' 
                    },
                    body: JSON.stringify(reportData) // 將 JavaScript 物件轉換為 JSON 字串
                });

                const result = await response.json();

                if (response.ok) {
                    // HTTP 狀態碼為 200-299，表示成功
                    showMessage(result.message, true);
                    // 清空表單
                    form.reset(); 
                } else {
                    // HTTP 狀態碼為 4xx 或 5xx，表示 API 發生錯誤
                    throw new Error(result.message || `API 錯誤：HTTP 狀態碼 ${response.status}`);
                }

            } catch (error) {
                // 處理網路錯誤或 API 返回的錯誤訊息
                console.error("提交失敗:", error);
                // 顯示錯誤訊息
                showMessage(`提交失敗: ${error.message}`, false);
            } finally {
                // 無論成功或失敗，都恢復按鈕狀態
                submitButton.disabled = false;
                submitButton.textContent = '送出報修單';
                submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        });
    </script>
</body>
</html>
    """
    return Response(html_content, mimetype='text/html')


# 2. API 路由：用於接收表單提交的資料
@app.route('/submit_report', methods=['POST'])
def submit_data_api():
    """
    接收來自網頁的 POST 請求，將 JSON 資料寫入 Google Sheets。
    """
    if not sheet:
        return jsonify({"status": "error", "message": "伺服器初始化失敗，無法連線至 Google Sheets。請檢查 log 訊息。"}), 500

    try:
        data = request.get_json()
    except Exception:
        logging.error("請求資料解析失敗：不是有效的 JSON 格式。")
        return jsonify({"status": "error", "message": "請求必須是 JSON 格式。請檢查網頁前端的 Content-Type。"}), 400

    if not data:
        logging.error("請求資料為空。")
        return jsonify({"status": "error", "message": "請求資料為空。"}), 400
    
    try:
        # 從 JSON 資料中提取欄位，確保 Key Name 大小寫正確！
        reporterName = data.get('reporterName', 'N/A')
        deviceLocation = data.get('deviceLocation', 'N/A')
        problemDescription = data.get('problemDescription', 'N/A')
        
        # 移除協辦老師欄位，將其值設為固定標記，以保持 Google Sheets 的欄位數一致性
        teacher_placeholder = "欄位已移除" 

        if not all([reporterName != 'N/A', deviceLocation != 'N/A', problemDescription != 'N/A']):
            logging.error(f"缺少必要資料: {data}")
            return jsonify({"status": "error", "message": "缺少必要的報修資料（如報修人、地點或描述）。"}), 400

        # 獲取當前的 UTC 時間
        utc_now = datetime.datetime.utcnow()
        # 加上 8 小時的偏移量 (台灣時區)
        taiwan_time = utc_now + datetime.timedelta(hours=8)
        timestamp = taiwan_time.strftime("%Y-%m-%d %H:%M:%S")

        row = [
            timestamp, 
            str(reporterName),
            str(deviceLocation),
            str(problemDescription),
            str(teacher_placeholder), # 使用佔位符號代替已移除的協辦老師欄位
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
# 本地測試運行
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
