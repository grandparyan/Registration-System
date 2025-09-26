import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# 載入 Jinja2 模板引擎來渲染 HTML
templates = Jinja2Templates(directory=".")

# 初始化 FastAPI 應用程式
app = FastAPI()

# 設定 Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    os.environ.get('SERVICE_ACCOUNT_CREDENTIALS'),
    scope
)
client = gspread.authorize(creds)

# 指定試算表
spreadsheet_id = os.environ.get('SPREADSHEET_ID', '1IHyA7aRxGJekm31KIbuORpg4-dVY8XTOEbU6p8vK3y4')
sheet = client.open_by_key(spreadsheet_id).get_worksheet(0) # 取得第一個工作表，您可以根據名稱修改為 get_worksheet_by_title('設備報修')

# 主頁面路由
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 處理表單提交的路由
@app.post("/submit")
async def process_form(
    reporterName: str = Form(...),
    deviceLocation: str = Form(...),
    problemDescription: str = Form(...),
    helperTeacher: str = Form(...)
):
    try:
        data = [
            str(datetime.now()), 
            reporterName, 
            deviceLocation, 
            problemDescription, 
            helperTeacher, 
            '待處理'
        ]
        sheet.append_row(data)
        return {"status": "success", "message": "報修已送出！"}
    except Exception as e:
        return {"status": "error", "message": f"送出失敗，請重試。錯誤訊息：{str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
