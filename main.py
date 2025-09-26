import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# 模板設定
templates = Jinja2Templates(directory=".")

# Google Sheets API 範圍
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
    print(f"錯誤：無法解析 SERVICE_ACCOUNT_CREDENTIALS 環境變數為 JSON。請檢查其格式。詳細錯誤: {e}")
    client = None

# 如果 client 成功建立，則打開試算表
sheet = None
if client:
    try:
        # 使用試算表 ID 連線，更為穩定
        spreadsheet_id = "1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4"
        sheet = client.open_by_key(spreadsheet_id).worksheet("設備報修")
        print("成功連線到 Google Sheets。")
    except gspread.exceptions.WorksheetNotFound:
        print("錯誤：找不到名稱為「設備報修」的工作表。")
    except gspread.exceptions.SpreadsheetNotFound:
        print("錯誤：找不到試算表ID為「1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4」的試算表。")
    except Exception as e:
        print(f"連線到 Google Sheets 時發生未知錯誤: {e}")

# 定義根路徑，提供 HTML 頁面
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 定義一個 API 端點來處理表單提交
@app.post("/submit", response_class=JSONResponse)
async def submit_form(request: Request):
    if not sheet:
        return JSONResponse(status_code=500, content={"status": "error", "message": "無法連線至 Google Sheets。請檢查後端設定。"})
    
    try:
        data = await request.json()
        
        reporterName = data.get('reporterName')
        deviceLocation = data.get('deviceLocation')
        problemDescription = data.get('problemDescription')
        helperTeacher = data.get('helperTeacher')
        
        # 獲取當前時間並寫入試算表
        row = [
            str(reporterName),
            str(deviceLocation),
            str(problemDescription),
            str(helperTeacher),
            "待處理"
        ]
        
        sheet.append_row(row)
        
        return JSONResponse(status_code=200, content={"status": "success", "message": "報修已送出！"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"提交失敗：{str(e)}"})
