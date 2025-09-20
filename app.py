from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import gspread
from pydantic import BaseModel
import os
import json
from datetime import datetime

# 你需要安裝以下函式庫：
# pip install fastapi uvicorn python-dotenv gspread pydantic

app = FastAPI()

# 加入 CORS 中間件，以允許前端網頁的跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中，請將此改為你的前端網址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 模型用於驗證請求的資料格式
class RepairRequest(BaseModel):
    reporterName: str
    equipment: str
    problemDescription: str
    assignedTeacher: str

# Google 服務帳戶憑證，來自你上傳的 JSON 檔案
SERVICE_ACCOUNT_CREDENTIALS = json.loads("""
{
  "type": "service_account",
  "project_id": "neat-cycling-472712-d9",
  "private_key_id": "26f5c58ecb1a16d21a6f959b7259581138329199",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDDOFpRlkrMeqsS\nTB8ScjanevPSwD8DTvyRIzhmX0F79o1pK6XkDw0rUQ9f2gqtGe6QDMFrHPnwPCY7\nYy5NPowdus09efAy+Z3xuBkatV9avk3dJMfWuMQMKYWr4/lI53q6I8UAMLNmMF7a\nbmUuCIncil+PLQ9GKVx1gdfmWvO8/h5KMOcPb0M+1nJQWj2XoklORfvIEozOgbk7\nNDr1Z1TfBm2xEgB6b8iLJ8al8F44viysD6gpyOMIcHxutX3ZEn8Fet/FvJ/ZLeP2\nB01SldRqy7egLB3kNbm9qzRMHvBWzhZQdLROTxMIzEPDx6FZClFX7nVyTLFDsWxW\nDmQUh2M7AgMBAAECggEAHhSn2McnaBHwHECoelzTo8OOoHHJA9x+5GpLPX2osc46\n2fLE0WWpqiayZMWh5tcGayHcB9eOLQCdBNedLH/acpZJxmhB+nN7bTc91F9lfa5c\ngcUyGcRHSSHOHBS5C7fHXGPjQ3U9n3MNRUEaIW66t3CG6vaO0kkl8GFSgDHm5BRK\n3Jl8/HZb3WLWSjHkldUROMbNvIg5lQwZrRD7C/1HIVo0aKRvQG7yvWFsroJXKku7\n98chcravAAw7ZAl/X9rNEoc5kTIieiC0uybew0D5Qr3sCD+RMRszuy4H1lKBAd8R\nxWIlj36vldyzuAr2SYAJK9r4jmAmYI/Pp5pc7Kc6yQKBgQD0VYj260iZgXheFPY6\nm+a7hGTDk+aM7lqN7ND+rhyuqa5RD9XAOfXKHSv0zumlLrjZM89G+oAo4CSmXKfD\nJmsBZP8Xx+0nYKcMXWBBlTIp/79M3Cwkfpn7RHWeUYGyf0iqIMworpVNQBYYRlvz\nAhLcCZSBdozCu0/kQlJHUsTe9wKBgQDMioDxNzS9xfO5XaKGDbK9J/j39ws319RB\nBONA88UH8dxL6ay+Rgxy8zkOlyRS5LcuFNLO320NtjQjmmSC4jDcE0frcB/XNU8S\n/Pm1UOltqwvFqRiWSKxYLHQRBbwK9BbpNn8oVZGOTYIeWzSLFQEbuCljNqwYzLjE\nLnzh+gJY3QKBgBA5nd7HwQpwjo2w1qkNsUTChe5249h3+4txLm+7ICx5GBpJ8ufQ\n8YF6bnDTTLCraZsC1cDg4aHVQJnLjVhoNLLjAg2SOS1kPbOUf8/bGHmxggKYnFXQ\nEmmdIjJhNzujODAT/Xq2HTQEDXOPOIvql1YFTNdMCAzmY2fE/7G8zVYBAoGBAKXK\nakOa7NwZ1LjeZbrk5YkfGlXbX7Nu9POSw6VFMeKDr320tbkwzCxsa0YhSmcKTlRC\nurDGNv3TPyXQokHYl6P62OPEaXqmEicg+EJ4iAzFhPA9ZNmDpHZ/6cBWdpomSV/V\nNXJ7EVVYC+0RHmDRsKlIN/vcN9iOMAGMcNs2K6rdAoGBAKTSGpkLGB+2hBO4bsuL\nKeyKzI1G7cgS+8mYG0FlKudCjZR7EL2Ktl5rz8rxjwoAjcRu5Kj6SRZjotTR/NXd\n2ooqBDGuU7NYXj51BrEKXPL/BSsj5cnmWcVoU71TlJKn/4+v095E8KZD8NLBjPlw\nvGKDxZwleIRAQBF3ckZXiAaR\n-----END PRIVATE KEY-----\n""")

# Google Sheets 設定
try:
    gc = gspread.service_account_from_dict(SERVICE_ACCOUNT_CREDENTIALS)
    spreadsheet = gc.open_by_key("YOUR_SPREADSHEET_ID_HERE")  # 請在此處填入你的試算表 ID
    worksheet = spreadsheet.worksheet("Sheet1")  # 如果你的工作表名稱不同，請更改此處
except Exception as e:
    print(f"連線到 Google Sheets 發生錯誤: {e}")
    worksheet = None

@app.post("/submit")
async def submit_repair_request(request: RepairRequest):
    """
    接收報修表單資料並寫入 Google Sheets.
    """
    if not worksheet:
        return {"error": "無法連線到 Google Sheets，請檢查後台配置。"}, 500

    try:
        # 準備要寫入的資料列
        row = [
            request.reporterName,
            request.equipment,
            request.problemDescription,
            request.assignedTeacher,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        # 將資料列附加到工作表中
        worksheet.append_row(row)
        
        return {"message": "資料已成功寫入 Google Sheets!"}
    
    except Exception as e:
        print(f"寫入 Google Sheets 時發生錯誤: {e}")
        return {"error": f"寫入 Google Sheets 時發生錯誤: {e}"}, 500

# 若要執行此 FastAPI 伺服器，請在終端機中輸入以下指令：
# uvicorn app:app --host 0.0.0.0 --port $PORT --reload
