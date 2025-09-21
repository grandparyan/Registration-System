from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import gspread
from pydantic import BaseModel
import json
from datetime import datetime
import os

# You'll need to install the following libraries:
# pip install fastapi uvicorn gspread pydantic

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

# Google Sheets service account setup
# Read credentials from an environment variable for security
def initialize_gspread_client():
    """
    Initializes and returns a gspread client.
    Handles potential connection errors gracefully.
    """
    try:
        creds_json = os.environ.get("GOOGLE_CREDS")
        if not creds_json:
            print("GOOGLE_CREDS environment variable not found.")
            return None
        
        SERVICE_ACCOUNT_CREDENTIALS = json.loads(creds_json)
        gc = gspread.service_account_from_dict(SERVICE_ACCOUNT_CREDENTIALS)
        
        # Replace "YOUR_SPREADSHEET_ID_HERE" with your actual Google Sheet ID
        spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        if not spreadsheet_id:
            print("SPREADSHEET_ID environment variable not found.")
            return None
        
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet_name = os.environ.get("WORKSHEET_NAME", "Sheet1")
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet
    
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

# Initialize worksheet on application startup
worksheet = initialize_gspread_client()

@app.get("/")
async def root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "Server is running! Try POST to /submit"}

@app.post("/submit")
async def submit_repair_request(request: RepairRequest):
    """
    Receives repair form data and writes it to Google Sheets.
    """
    # Check if the worksheet was successfully initialized
    if not worksheet:
        raise HTTPException(status_code=500, detail="Cannot connect to Google Sheets. Please check server configuration.")

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
        
        return {"message": "Data successfully written to Google Sheets!"}
    
    except Exception as e:
        print(f"Error writing to Google Sheets: {e}")
        raise HTTPException(status_code=500, detail=f"Error writing to Google Sheets: {e}")
