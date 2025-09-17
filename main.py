import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor

# --- Pydantic Models ---
class Report(BaseModel):
    reporter_name: str
    location: str
    problem_description: str

class ReportUpdate(BaseModel):
    reporter_name: Optional[str] = None
    location: Optional[str] = None
    problem_description: Optional[str] = None

# Models for Admin Batch Operations
class BatchUpdateRequest(BaseModel):
    ids: List[int]
    status: str

class BatchDeleteRequest(BaseModel):
    ids: List[int]

# --- FastAPI Application Instance ---
# 這就是 Gunicorn 指令中 main:app 或 app:app 裡的第二個 'app'
app = FastAPI()

# --- Database Connection ---
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Establishes and returns a PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def initialize_db():
    """Creates the reports table if it doesn't exist with the new status column."""
    conn = get_db_connection()
    if not conn:
        print("Could not connect to the database for initialization.")
        return
    with conn.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            reporter_name VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            problem_description TEXT,
            status VARCHAR(50) NOT NULL DEFAULT '待處理'
        );
        -- Add status column if it doesn't exist (for migration)
        DO $$
        BEGIN
            ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT '待處理';
        EXCEPTION
            WHEN duplicate_column THEN
                -- Column already exists, do nothing.
        END
        $$;
        """)
        conn.commit()
    conn.close()

# Initialize database on startup
initialize_db()

# ========== USER-FACING ENDPOINTS (for index.html) ==========

@app.get("/", include_in_schema=False)
async def read_index():
    """Serves the main user-facing HTML page (index.html)."""
    return FileResponse('index.html')

@app.post("/reports/", response_model=Report, status_code=201, tags=["User"])
def create_report(report: Report):
    """Creates a new repair report."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        query = "INSERT INTO reports (reporter_name, location, problem_description) VALUES (%s, %s, %s) RETURNING id"
        cursor.execute(query, (report.reporter_name, report.location, report.problem_description))
        new_report_id = cursor.fetchone()['id']
        conn.commit()
    conn.close()
    return {"id": new_report_id, **report.dict()}

@app.get("/reports/", response_model=List[dict], tags=["User", "Student"])
def read_reports():
    """Gets all repair reports for all views."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM reports ORDER BY id ASC")
        reports = cursor.fetchall()
    conn.close()
    return reports

@app.put("/reports/{report_id}", response_model=dict, tags=["User"])
def update_report(report_id: int, report: ReportUpdate):
    """Updates a specific repair report."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    update_data = report.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    query = f"UPDATE reports SET {set_clause} WHERE id = %s"
    values = list(update_data.values()) + [report_id]

    with conn.cursor() as cursor:
        cursor.execute(query, values)
        affected_rows = cursor.rowcount
        conn.commit()
    conn.close()

    if affected_rows == 0:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    return {"message": f"Report ID {report_id} has been updated"}

@app.delete("/reports/{report_id}", response_model=dict, tags=["User"])
def delete_report(report_id: int):
    """Deletes a specific repair report."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    with conn.cursor() as cursor:
        query = "DELETE FROM reports WHERE id = %s"
        cursor.execute(query, (report_id,))
        affected_rows = cursor.rowcount
        conn.commit()
    conn.close()
    if affected_rows == 0:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    return {"message": f"Report ID {report_id} has been deleted"}

# ========== ADMIN / TEACHER ENDPOINTS (for teacher.html) ==========

@app.get("/teacher/", include_in_schema=False)
async def read_teacher_index():
    """Serves the information teacher's HTML page (teacher.html)."""
    return FileResponse('teacher.html')

@app.get("/admin/reports/", response_model=List[dict], tags=["Admin"])
def admin_read_reports():
    """Gets all reports for the admin/teacher view."""
    return read_reports()

@app.post("/admin/reports/batch-update", response_model=dict, tags=["Admin"])
def admin_batch_update_status(request: BatchUpdateRequest):
    """Updates the status for multiple reports at once."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    query = "UPDATE reports SET status = %s WHERE id = ANY(%s)"
    with conn.cursor() as cursor:
        cursor.execute(query, (request.status, request.ids))
        affected_rows = cursor.rowcount
        conn.commit()
    conn.close()
    
    return {"message": f"Successfully updated {affected_rows} reports to '{request.status}'."}

@app.post("/admin/reports/batch-delete", response_model=dict, tags=["Admin"])
def admin_batch_delete(request: BatchDeleteRequest):
    """Deletes multiple reports at once."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    query = "DELETE FROM reports WHERE id = ANY(%s)"
    with conn.cursor() as cursor:
        cursor.execute(query, (request.ids,))
        affected_rows = cursor.rowcount
        conn.commit()
    conn.close()

    return {"message": f"Successfully deleted {affected_rows} reports."}

# ========== STUDENT ENDPOINT (for student.html) ==========

@app.get("/student/", include_in_schema=False)
async def read_student_index():
    """Serves the student-facing HTML page (student.html)."""
    return FileResponse('student.html')

