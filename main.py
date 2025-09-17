# 這是您的後台服務主程式碼。
# 檔案名稱: main.py

import os
import json
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# 確保已經安裝所有必要的函式庫:
# pip install fastapi uvicorn sqlalchemy pydantic pymysql

# --- 資料庫連線設定 ---
# 為了部署到 Render，我們使用環境變數來儲存資料庫憑證。
# 請在 Render 上設定這些變數:
# MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DATABASE
DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_DATABASE = os.getenv("MYSQL_DATABASE")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_DATABASE]):
    print("Warning: Database environment variables are not set. Using placeholders for local development.")
    DB_USER = "user"
    DB_PASSWORD = "password"
    DB_HOST = "localhost"
    DB_DATABASE = "repair_db"

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 建立 FastAPI 應用程式實例
app = FastAPI(
    title="報修系統後台服務",
    description="由 FastAPI 驅動，為學校報修系統提供 API 介面。"
)

# --- 資料庫模型 (SQLAlchemy ORM) ---
# 定義資料表結構

class RepairRequest(Base):
    """普通老師填寫的報修單資料表"""
    __tablename__ = "repair_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    requester_name = Column(String(255), nullable=False) # 報修者姓名
    location = Column(String(255), nullable=False)       # 設備地點
    issue = Column(String(500), nullable=False)          # 設備問題
    is_task_assigned = Column(Boolean, default=False)    # 是否已轉為任務

class Task(Base):
    """資訊老師發布的任務資料表"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    description = Column(String(500), nullable=False)      # 任務描述 (從報修單問題轉移)
    max_students = Column(Integer, nullable=False)         # 任務所需人數
    assigned_students_json = Column(String(1000), default="[]") # 已簽到的學生名單 (JSON格式)
    is_completed = Column(Boolean, default=False)          # 任務是否完成

    @property
    def assigned_students(self) -> List[str]:
        """從 JSON 字串轉換為 Python 列表"""
        return json.loads(self.assigned_students_json)

    @assigned_students.setter
    def assigned_students(self, students: List[str]):
        """將 Python 列表轉換為 JSON 字串"""
        self.assigned_students_json = json.dumps(students)

# 創建資料表 (如果不存在)
# 備註：在 Render 上，您通常會使用 Alembic 等工具來管理資料庫遷移，
# 但對於這個簡單的範例，直接創建資料表即可。
Base.metadata.create_all(bind=engine)

# --- 資料驗證模型 (Pydantic) ---
# 定義 API 傳輸的資料格式

class RepairRequestBase(BaseModel):
    requester_name: str
    location: str
    issue: str

class RepairRequestCreate(RepairRequestBase):
    pass

class RepairRequestResponse(RepairRequestBase):
    id: int
    is_task_assigned: bool

    class Config:
        orm_mode = True

class TaskBase(BaseModel):
    description: str
    max_students: int

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    assigned_students: List[str]
    is_completed: bool

    class Config:
        orm_mode = True

class StudentSignup(BaseModel):
    student_name: str

# --- 資料庫連線依賴性 (Dependency) ---
# 每次 API 請求都會建立一個新的資料庫會話
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API 端點 (Routes) ---

@app.get("/")
def read_root():
    return {"message": "歡迎使用報修系統後台服務！"}

# --- 普通老師權限 ---
@app.post("/repair_requests/", status_code=status.HTTP_201_CREATED)
def create_repair_request(request: RepairRequestCreate, db: Session = Depends(get_db)):
    """
    **普通老師** 建立新的報修單。
    """
    db_request = RepairRequest(**request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return {"message": "報修單已成功提交！", "id": db_request.id}

# --- 資訊老師權限 ---
@app.get("/repair_requests/", response_model=List[RepairRequestResponse])
def get_all_repair_requests(db: Session = Depends(get_db)):
    """
    **資訊老師** 檢視所有報修單。
    """
    requests = db.query(RepairRequest).all()
    return requests

@app.delete("/repair_requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repair_request(request_id: int, db: Session = Depends(get_db)):
    """
    **資訊老師** 刪除報修單。
    """
    request = db.query(RepairRequest).filter(RepairRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="找不到報修單")
    db.delete(request)
    db.commit()
    return

@app.post("/tasks/from_request/{request_id}", status_code=status.HTTP_201_CREATED)
def create_task_from_request(
    request_id: int,
    task_info: TaskCreate,
    db: Session = Depends(get_db)
):
    """
    **資訊老師** 將報修單轉為任務。
    """
    repair_request = db.query(RepairRequest).filter(RepairRequest.id == request_id).first()
    if not repair_request:
        raise HTTPException(status_code=404, detail="找不到報修單")
    if repair_request.is_task_assigned:
        raise HTTPException(status_code=400, detail="此報修單已轉為任務")
        
    db_task = Task(
        description=task_info.description,
        max_students=task_info.max_students,
        assigned_students_json=json.dumps([]) # 初始為空列表
    )
    db.add(db_task)
    
    # 更新報修單狀態
    repair_request.is_task_assigned = True
    
    db.commit()
    db.refresh(db_task)
    return {"message": "任務已成功發布！", "task_id": db_task.id}

@app.put("/tasks/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db)):
    """
    **資訊老師** 將任務標記為完成。
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="找不到任務")
    task.is_completed = True
    db.commit()
    db.refresh(task)
    return {"message": "任務已標記為完成！"}

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    **資訊老師** 刪除任務。
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="找不到任務")
    db.delete(task)
    db.commit()
    return

# --- 學生權限 ---
@app.get("/tasks/", response_model=List[TaskResponse])
def get_all_tasks(db: Session = Depends(get_db)):
    """
    **學生** 檢視所有尚未完成的任務。
    """
    tasks = db.query(Task).filter(Task.is_completed == False).all()
    # 由於 assigned_students 是 @property，Pydantic 會自動處理
    return tasks

@app.post("/tasks/{task_id}/signup")
def signup_for_task(task_id: int, student: StudentSignup, db: Session = Depends(get_db)):
    """
    **學生** 報名參加任務。
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="找不到任務")
    if task.is_completed:
        raise HTTPException(status_code=400, detail="此任務已完成，無法報名")

    current_students = task.assigned_students
    if len(current_students) >= task.max_students:
        raise HTTPException(status_code=400, detail="此任務人數已滿")
    if student.student_name in current_students:
        raise HTTPException(status_code=400, detail="您已報名此任務")
    
    current_students.append(student.student_name)
    task.assigned_students = current_students
    
    db.commit()
    db.refresh(task)
    return {"message": f"成功報名任務 {task_id}！"}
