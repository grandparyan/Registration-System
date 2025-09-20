from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import gspread
from pydantic import BaseModel
import os
import json
from datetime import datetime

# You'll need to install the following libraries:
# pip install fastapi uvicorn python-dotenv gspread pydantic

app = FastAPI()

# Add CORS middleware to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request body validation
class RepairRequest(BaseModel):
    reporterName: str
    equipment: str
    problemDescription: str
    assignedTeacher: str

# Google Sheets service account credentials from the uploaded JSON
# NOTE: For production, store these securely in environment variables.
# DO NOT hardcode them in a public repository.
SERVICE_ACCOUNT_CREDENTIALS = json.loads("""
{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID_HERE",
  "private_key_id": "YOUR_PRIVATE_KEY_ID_HERE",
  "private_key": "YOUR_PRIVATE_KEY_HERE",
  "client_email": "YOUR_CLIENT_EMAIL_HERE",
  "client_id": "YOUR_CLIENT_ID_HERE",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/YOUR_CLIENT_X509_CERT_URL_HERE",
  "universe_domain": "googleapis.com"
}
""")

# Google Sheets setup
try:
    gc = gspread.service_account_from_dict(SERVICE_ACCOUNT_CREDENTIALS)
    spreadsheet = gc.open_by_key("YOUR_SPREADSHEET_ID_HERE")  # Use the spreadsheet ID
    worksheet = spreadsheet.worksheet("Sheet1")  # Change "Sheet1" if your worksheet has a different name
except Exception as e:
    print(f"Error connecting to Google Sheets: {e}")
    worksheet = None

@app.post("/submit")
async def submit_repair_request(request: RepairRequest):
    """
    接收報修表單資料並寫入 Google Sheets.
    """
    if not worksheet:
        return {"error": "無法連接到 Google Sheets，請檢查後台配置。"}, 500

    try:
        # Prepare the data row
        row = [
            request.reporterName,
            request.equipment,
            request.problemDescription,
            request.assignedTeacher,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        # Append the row to the worksheet
        worksheet.append_row(row)
        
        return {"message": "資料已成功寫入 Google Sheets!"}
    
    except Exception as e:
        print(f"寫入 Google Sheets 時發生錯誤: {e}")
        return {"error": f"寫入 Google Sheets 時發生錯誤: {e}"}, 500

# To run the FastAPI server, use the command:
# uvicorn app:app --reload
