import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import mysql.connector

# 定義 Pydantic 模型用於資料驗證
class RepairReport(BaseModel):
    reporter_name: str
    location: str
    problem_description: str

# 建立 FastAPI 應用程式實例
app = FastAPI()

# 設定靜態檔案，以便可以提供 HTML 檔案
app.mount("/static", StaticFiles(directory="."), name="static")

# 假設你的 Render MySQL 資料庫連線資訊
# 建議將這些資訊設定為環境變數，以確保安全性
DB_HOST = os.environ.get("DB_HOST", "your_database_host")
DB_USER = os.environ.get("DB_USER", "your_database_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "your_database_password")
DB_DATABASE = os.environ.get("DB_DATABASE", "your_database_name")

# 嘗試建立資料庫連線
try:
    db_connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE
    )
    db_cursor = db_connection.cursor()
    print("成功連線到 MySQL 資料庫！")
except mysql.connector.Error as err:
    print(f"資料庫連線失敗: {err}")
    db_connection = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    提供主頁面 (index.html)。
    """
    return FileResponse("index.html")

@app.post("/submit_report")
async def submit_report(
    reporter_name: str = Form(...),
    location: str = Form(...),
    problem_description: str = Form(...)
):
    """
    接收報修表單資料並將其寫入資料庫。
    """
    if db_connection is None:
        return {"status": "error", "message": "無法連線到資料庫。"}

    try:
        # SQL 插入語句，將資料存入你的資料表
        # 請確保你的資料表名為 `repair_reports` 且欄位為 `reporter_name`, `location`, `problem_description`
        # 建議創建資料表時，將 ID 欄位設定為 AUTO_INCREMENT，例如:
        # CREATE TABLE repair_reports (
        #   id INT AUTO_INCREMENT PRIMARY KEY,
        #   reporter_name VARCHAR(255),
        #   location VARCHAR(255),
        #   problem_description TEXT,
        #   report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        # );

        sql = "INSERT INTO repair_reports (reporter_name, location, problem_description) VALUES (%s, %s, %s)"
        val = (reporter_name, location, problem_description)
        db_cursor.execute(sql, val)
        db_connection.commit()

        return {"status": "success", "message": "報修單已成功提交！"}
    except mysql.connector.Error as err:
        db_connection.rollback()
        return {"status": "error", "message": f"資料庫寫入失敗: {err}"}
    finally:
        # 為了簡化，這裡不關閉連線，實際生產環境可能需要使用連線池
        pass
