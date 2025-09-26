import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets API 範圍，這是必須的
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 從環境變數中讀取服務帳號憑證並解析為 JSON
try:
    creds_json = os.environ.get('SERVICE_ACCOUNT_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            scope
        )
        client = gspread.authorize(creds)
    else:
        print("錯誤：找不到 SERVICE_ACCOUNT_CREDENTIALS 環境變數。")
        client = None
except json.JSONDecodeError as e:
    print(f"錯誤：無法解析 SERVICE_ACCOUNT_CREDENTIALS 環境變數為 JSON。詳細錯誤: {e}")
    client = None

# 如果 client 成功建立，則打開試算表
sheet = None
if client:
    try:
        # 使用試算表 ID 連線
        spreadsheet_id = "1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4"
        sheet = client.open_by_key(spreadsheet_id).worksheet("設備報修")
        print("成功連線到 Google Sheets。")
    except gspread.exceptions.WorksheetNotFound:
        print("錯誤：找不到名稱為「設備報修」的工作表。")
    except gspread.exceptions.SpreadsheetNotFound:
        print("錯誤：找不到試算表ID為「1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4」的試算表。")
    except Exception as e:
        print(f"連線到 Google Sheets 時發生未知錯誤: {e}")

# 這個函式模擬從你的網路服務接收到的資料
def submit_data(data):
    """
    處理從網路服務接收到的資料並寫入 Google Sheets。
    """
    if not sheet:
        print("無法連線至 Google Sheets。")
        return {"status": "error", "message": "無法連線至 Google Sheets。請檢查後端設定。"}
    
    try:
        reporterName = data.get('reporterName')
        deviceLocation = data.get('deviceLocation')
        problemDescription = data.get('problemDescription')
        helperTeacher = data.get('helperTeacher')

        # 這裡可以加入時間欄位，或根據您的需求調整
        row = [
            str(reporterName),
            str(deviceLocation),
            str(problemDescription),
            str(helperTeacher),
            "待處理"
        ]
        
        sheet.append_row(row)
        
        return {"status": "success", "message": "資料已送出！"}
    except Exception as e:
        return {"status": "error", "message": f"提交失敗：{str(e)}"}

# 這裡可以是你從 GitHub 網頁服務接收 JSON 資料的模擬範例
if __name__ == "__main__":
    # 這是從網頁表單傳來的 JSON 資料範例
    sample_data = {
        "reporterName": "張三",
        "deviceLocation": "101教室",
        "problemDescription": "投影機無法開機",
        "helperTeacher": "李老師"
    }
    
    result = submit_data(sample_data)
    print(result)
