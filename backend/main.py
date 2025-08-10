import os, json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# =============== ENV ===============
DATABASE_URL = os.getenv("DATABASE_URL")  # dạng postgresql://USER:PASS@HOST:PORT/DB?sslmode=require
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

# =============== DB ===============
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============== Google Sheets ===============
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_sheets_service = None

def get_sheets_service():
    global _sheets_service
    if _sheets_service is None:
        if not SERVICE_ACCOUNT_JSON:
            raise RuntimeError("GCP_SERVICE_ACCOUNT_JSON env var is missing")
        info = json.loads(SERVICE_ACCOUNT_JSON)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        _sheets_service = build("sheets", "v4", credentials=creds)
    return _sheets_service

SHEET_TAB = "Accounts"
HEADERS = [
    "id","platform","username","email","password","phone","note","two_factor_enabled","tags","created_at","updated_at"
]

# =============== Pydantic Schemas ===============
class AccountIn(BaseModel):
    platform: str
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    note: Optional[str] = None
    two_factor_enabled: Optional[bool] = False
    tags: Optional[str] = None

class AccountOut(AccountIn):
    id: int
    created_at: datetime
    updated_at: datetime

# =============== FastAPI ===============
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

# =============== Helpers ===============

def row_to_dict(row):
    cols = ["id","platform","username","email","password","phone","note","two_factor_enabled","tags","created_at","updated_at"]
    return dict(zip(cols, row))

# Full snapshot sync: ghi toàn bộ DB ra sheet mỗi khi có thay đổi

def sync_all_to_sheet(db):
    if not SPREADSHEET_ID:
        return  # cho phép chạy tạm khi chưa cấu hình sheet

    rows = db.execute(text(
        """
        select id, platform, coalesce(username,''), coalesce(email,''), coalesce(password,''),
               coalesce(phone,''), coalesce(note,''), coalesce(two_factor_enabled,false)::text,
               coalesce(tags,''), to_char(created_at,'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
               to_char(updated_at,'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        from accounts
        order by id asc
        """
    )).all()

    values = [HEADERS]
    for r in rows:
        values.append(list(r))

    service = get_sheets_service()
    body = {"values": values}

    # Clear + Update
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_TAB}!A:Z"
    ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="RAW",
        body=body
    ).execute()

# =============== CRUD Endpoints ===============
@app.post("/accounts", response_model=AccountOut)
def create_account(payload: AccountIn, db=Depends(get_db)):
    insert_sql = text(
        """
        insert into accounts (platform, username, email, password, phone, note, two_factor_enabled, tags)
        values (:platform, :username, :email, :password, :phone, :note, :two_factor_enabled, :tags)
        returning id, platform, username, email, password, phone, note, two_factor_enabled, tags, created_at, updated_at
        """
    )
    row = db.execute(insert_sql, payload.model_dump())
    db.commit()
    data = row_to_dict(row.fetchone())
    sync_all_to_sheet(db)
    return data

@app.get("/accounts", response_model=List[AccountOut])
def list_accounts(db=Depends(get_db)):
    rows = db.execute(text(
        "select id, platform, username, email, password, phone, note, two_factor_enabled, tags, created_at, updated_at from accounts order by id desc"
    )).all()
    return [row_to_dict(r) for r in rows]

@app.get("/accounts/search", response_model=List[AccountOut])
def search_accounts(q: str, db=Depends(get_db)):
    rows = db.execute(text(
        """
        select id, platform, username, email, password, phone, note, two_factor_enabled, tags, created_at, updated_at
        from accounts
        where (platform ilike :kw or username ilike :kw or email ilike :kw or tags ilike :kw)
        order by updated_at desc
        """
    ), {"kw": f"%{q}%"}).all()
    return [row_to_dict(r) for r in rows]

@app.put("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountIn, db=Depends(get_db)):
    update_sql = text(
        """
        update accounts set
          platform = :platform,
          username = :username,
          email = :email,
          password = :password,
          phone = :phone,
          note = :note,
          two_factor_enabled = :two_factor_enabled,
          tags = :tags
        where id = :id
        returning id, platform, username, email, password, phone, note, two_factor_enabled, tags, created_at, updated_at
        """
    )
    row = db.execute(update_sql, {**payload.model_dump(), "id": account_id})
    if row.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Not found")
    db.commit()
    data = row_to_dict(row.fetchone())
    sync_all_to_sheet(db)
    return data

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db=Depends(get_db)):
    r = db.execute(text("delete from accounts where id=:id"), {"id": account_id})
    if r.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Not found")
    db.commit()
    sync_all_to_sheet(db)
    return {"ok": True}

