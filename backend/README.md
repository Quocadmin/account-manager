# Backend (FastAPI)

## Chạy local (tuỳ chọn)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://USER:PASS@HOST:PORT/DB?sslmode=require"
export GOOGLE_SHEETS_SPREADSHEET_ID="<ID>"
export GCP_SERVICE_ACCOUNT_JSON='{"type":"service_account", ...}'
uvicorn main:app --host 0.0.0.0 --port 8000

