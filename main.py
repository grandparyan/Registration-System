import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from psycopg2.extras import RealDictCursor
import datetime

# --- Pydantic 資料模型 (定義 API 的輸入和輸出格式) ---

# 普通教師提交報修時的資料格式
class ReportCreate(BaseModel):
    reporter_name: str = Field(..., description="報修者姓名")
    location: str = Field(..., description="問題設備地點")
    problem_description: str = Field(..., description="設備問題描述")

# 資訊老師發布任務時的輸入格式
class TaskPublish(BaseModel):
    required_students: int = Field(gt=0, description="需要的學生人數 (必須大於 0)")

# 學生報名參加任務時的輸入格式
class StudentSignup(BaseModel):
    student_name: str = Field(..., min_length=2, description="報名學生的姓名")

# --- FastAPI 應用程式實例 ---
# 為了避免部署混淆，我們統一將檔案命名為 main.py，並使用 app 這個變數
app = FastAPI(
    title="學校設備報修系統 API",
    description="一個為教師和學生設計的設備報修與任務系統後端",
    version="1.0.0",
)

# --- 資料庫連線設定 ---
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """建立並返回一個 PostgreSQL 資料庫連線"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"資料庫連線錯誤: {e}")
        return None

def initialize_database():
    """
    應用程式啟動時執行，確保所有需要的資料表都已建立。
    - reports: 儲存所有報修單和由報修單轉換而來的任務。
    - task_signups: 儲存學生報名任務的紀錄。
    """
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("啟動時無法連線至資料庫，請檢查 DATABASE_URL 環境變數")
    
    with conn.cursor() as cursor:
        # 建立報修/任務主表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            reporter_name VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            problem_description TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT '待處理',
            is_task BOOLEAN NOT NULL DEFAULT FALSE,
            required_students INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # 建立學生任務報名表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_signups (
            id SERIAL PRIMARY KEY,
            report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
            student_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(report_id, student_name)
        );
        """)
        conn.commit()
    conn.close()
    print("資料庫初始化完成。")

# --- 應用程式生命週期事件 ---
@app.on_event("startup")
def on_startup():
    """應用程式啟動時，自動檢查並建立資料表"""
    initialize_database()

# --- API 端點 (Endpoints) ---

# ===============================================
# ===         1. 普通教師相關 API             ===
# ===============================================

@app.post("/reports", summary="普通教師提交新的報修單", status_code=201, tags=["普通教師"])
def create_new_report(report: ReportCreate):
    """
    提供給普通教師使用。
    - 接收報修者姓名、地點和問題描述。
    - 在資料庫中建立一筆新的 `reports` 紀錄。
    - 預設狀態為 '待處理'，且 `is_task` 為 `FALSE`。
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="無法連線至資料庫")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """
        INSERT INTO reports (reporter_name, location, problem_description)
        VALUES (%s, %s, %s)
        RETURNING *;
        """
        cursor.execute(query, (report.reporter_name, report.location, report.problem_description))
        new_report = cursor.fetchone()
        conn.commit()
    conn.close()
    return {"message": "報修單已成功提交", "data": new_report}

# ===============================================
# ===         2. 資訊老師相關 API             ===
# ===============================================

@app.get("/admin/reports", summary="資訊老師獲取所有報修單與任務列表", tags=["資訊老師"])
def get_all_reports_for_admin():
    """
    提供給資訊老師的管理介面使用。
    - 查詢 `reports` 表中的所有紀錄。
    - 對於每一筆紀錄，同時查詢 `task_signups` 表，計算並附上當前已報名人數。
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="無法連線至資料庫")
        
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # 使用 LEFT JOIN 和 GROUP BY 來計算每個任務的已報名人數
        query = """
        SELECT 
            r.*, 
            COUNT(ts.id) as current_students
        FROM reports r
        LEFT JOIN task_signups ts ON r.id = ts.report_id
        GROUP BY r.id
        ORDER BY r.id DESC;
        """
        cursor.execute(query)
        reports = cursor.fetchall()
    conn.close()
    return reports

@app.post("/admin/reports/{report_id}/publish", summary="資訊老師將報修單發布為任務", tags=["資訊老師"])
def publish_report_as_task(report_id: int, task_data: TaskPublish):
    """
    提供給資訊老師使用，將一個待處理的報修單轉換為一個需要學生協助的任務。
    - 設定 `is_task` 為 `TRUE`。
    - 設定 `required_students` (所需學生人數)。
    - 更新狀態為 '已發佈為任務'。
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="無法連線至資料庫")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """
        UPDATE reports
        SET is_task = TRUE, required_students = %s, status = '已發佈為任務'
        WHERE id = %s AND is_task = FALSE
        RETURNING *;
        """
        cursor.execute(query, (task_data.required_students, report_id))
        updated_task = cursor.fetchone()
        conn.commit()
    conn.close()
    
    if not updated_task:
        raise HTTPException(status_code=404, detail=f"找不到ID為 {report_id} 的報修單，或該項目已是任務。")
        
    return {"message": "成功發布為任務", "data": updated_task}

@app.delete("/admin/reports/{report_id}", summary="資訊老師刪除報修單或任務", status_code=204, tags=["資訊老師"])
def delete_report_or_task(report_id: int):
    """
    提供給資訊老師使用。
    - 刪除 `reports` 表中的指定紀錄。
    - 由於資料庫設定了 `ON DELETE CASCADE`，對應的學生報名紀錄 (`task_signups`) 也會被自動刪除。
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="無法連線至資料庫")
        
    with conn.cursor() as cursor:
        query = "DELETE FROM reports WHERE id = %s;"
        cursor.execute(query, (report_id,))
        # 檢查是否有資料被刪除
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail=f"找不到ID為 {report_id} 的項目。")
        conn.commit()
    conn.close()
    return # 成功刪除時，HTTP 204 不需要回傳任何內容

# ===============================================
# ===           3. 學生相關 API               ===
# ===============================================

@app.get("/tasks", summary="學生獲取所有已發布的任務列表", tags=["學生"])
def get_published_tasks_for_students():
    """
    提供給學生介面使用。
    - 只查詢 `is_task` 為 `TRUE` 的紀錄。
    - 同時計算每個任務的已報名人數和報名學生名單。
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="無法連線至資料庫")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # 使用彙總函數 ARRAY_AGG 來收集學生名單
        query = """
        SELECT 
            r.id, r.location, r.problem_description, r.required_students, r.status,
            COALESCE(COUNT(ts.id), 0) as current_students,
            COALESCE(ARRAY_AGG(ts.student_name) FILTER (WHERE ts.student_name IS NOT NULL), '{}') as signed_up_students
        FROM reports r
        LEFT JOIN task_signups ts ON r.id = ts.report_id
        WHERE r.is_task = TRUE
        GROUP BY r.id
        ORDER BY r.id DESC;
        """
        cursor.execute(query)
        tasks = cursor.fetchall()
    conn.close()
    return tasks

@app.post("/tasks/{task_id}/signup", summary="學生報名參加任務", tags=["學生"])
def signup_for_task(task_id: int, signup_data: StudentSignup):
    """
    提供給學生報名任務使用。
    - **交易控制 (Transaction)**：確保在檢查人數和寫入報名資料之間，資料庫狀態不會被其他人改變，避免超額報名。
    - 檢查任務是否存在且已發布。
    - 檢查是否還有名額。
    - 檢查學生是否已經報名過。
    - 寫入一筆新的 `task_signups` 紀錄。
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="無法連線至資料庫")
        
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 步驟 1: 鎖定任務資料列，並取得所需人數和目前人數
            # FOR UPDATE 會鎖定該行，直到交易結束，防止其他使用者同時報名
            cursor.execute("""
            SELECT 
                r.required_students, 
                COUNT(ts.id) as current_students
            FROM reports r
            LEFT JOIN task_signups ts ON r.id = ts.report_id
            WHERE r.id = %s AND r.is_task = TRUE
            GROUP BY r.id
            FOR UPDATE;
            """, (task_id,))
            
            task_info = cursor.fetchone()
            if not task_info:
                raise HTTPException(status_code=404, detail="找不到此任務，或任務尚未發布。")

            # 步驟 2: 檢查人數是否已滿
            if task_info['current_students'] >= task_info['required_students']:
                raise HTTPException(status_code=400, detail="此任務名額已滿！")

            # 步驟 3: 檢查學生是否重複報名 (雖然資料庫有 UNIQUE 限制，但在 API 層先檢查可以提供更友善的錯誤訊息)
            cursor.execute("SELECT id FROM task_signups WHERE report_id = %s AND student_name = %s;", (task_id, signup_data.student_name))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"'{signup_data.student_name}' 您已經報名過此任務了。")

            # 步驟 4: 插入新的報名紀錄
            cursor.execute("""
            INSERT INTO task_signups (report_id, student_name)
            VALUES (%s, %s)
            RETURNING *;
            """, (task_id, signup_data.student_name))
            
            new_signup = cursor.fetchone()
            
            # 如果一切順利，提交交易
            conn.commit()
            
            return {"message": f"'{signup_data.student_name}' 您已成功報名！", "data": new_signup}

    except psycopg2.Error as e:
        # 如果發生任何資料庫錯誤，回滾交易
        conn.rollback()
        # 檢查是否為我們自訂的重複報名錯誤
        if e.pgcode == '23505': # Unique violation
             raise HTTPException(status_code=400, detail=f"'{signup_data.student_name}' 您已經報名過此任務了。")
        raise HTTPException(status_code=500, detail=f"資料庫操作失敗: {e}")
    except HTTPException:
        # 如果是我們主動拋出的 HTTP 錯誤 (如名額已滿)，則直接重新拋出
        conn.rollback()
        raise
    finally:
        # 確保連線最後一定會被關閉
        if conn:
            conn.close()

