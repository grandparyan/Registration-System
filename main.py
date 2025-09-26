import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(creds_json),
            scope
        )
        client = gspread.authorize(creds)
    else:
        print("錯誤：找不到 SERVICE_ACCOUNT_CREDENTIALS 環境變數。")
        client = None # 避免後續程式碼因 client 為 None 而崩潰
except json.JSONDecodeError:
    print("錯誤：無法解析 SERVICE_ACCOUNT_CREDENTIALS 環境變數為 JSON。請檢查其格式。")
    client = None

# 如果 client 成功建立，則打開試算表
if client:
    sheet = client.open("設備報修表單").worksheet("設備報修")
else:
    sheet = None

# 定義根路徑，提供 HTML 頁面
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 這裡可以根據需要從 Google Sheets 讀取資料
    # 例如：data = sheet.get_all_records()
    # 然後傳遞給模板
    return templates.TemplateResponse("index.html", {"request": request})

# 定義一個 API 端點來處理表單提交
@app.post("/submit", response_class=HTMLResponse)
async def submit_form(request: Request):
    if not sheet:
        return {"status": "error", "message": "無法連線至 Google Sheets。"}
    
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
        
        return {"status": "success", "message": "報修已送出！"}
    except Exception as e:
        return {"status": "error", "message": f"提交失敗：{str(e)}"}
