from pathlib import Path
import re
import fitz
from docx import Document
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .analyzer import analyze_resume, clean_text

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
app = FastAPI(title="ATS Resume Analyzer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

MAX_BYTES = 5 * 1024 * 1024

async def extract_resume(file: UploadFile) -> str:
    filename = (file.filename or "").lower()
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Please upload a PDF or DOCX file.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. Maximum size is 5 MB.")
    try:
        if filename.endswith(".pdf"):
            with fitz.open(stream=data, filetype="pdf") as pdf:
                text = "\n".join(page.get_text("text") for page in pdf)
        else:
            import io
            doc = Document(io.BytesIO(data))
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(parts)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this document. Try exporting it again as a text-based PDF or DOCX.") from exc
    text = clean_text(text)
    if len(text) < 40:
        raise HTTPException(status_code=422, detail="Very little text was extracted. This may be a scanned/image-only PDF. Try a text-based PDF or DOCX.")
    return text

@app.get("/", response_class=HTMLResponse)
async def home():
    return (FRONTEND / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ATS Resume Analyzer"}

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), job_description: str = Form(...)):
    jd = clean_text(job_description)
    if len(jd) < 50:
        raise HTTPException(status_code=400, detail="Please paste a more complete job description (at least 50 characters).")
    if len(jd) > 30000:
        raise HTTPException(status_code=400, detail="The job description is too long. Maximum 30,000 characters.")
    resume_text = await extract_resume(file)
    return analyze_resume(resume_text, jd, file.filename or "resume")
