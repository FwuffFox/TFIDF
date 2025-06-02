from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.tfidf import TFIDFCalculator
from typing import Optional
import uuid

app = FastAPI()
tfidf_calculator = TFIDFCalculator()
templates = Jinja2Templates(directory="app/templates")
document_store = {}

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None)):
    try:
        if text is None and file is not None:
            text = (await file.read()).decode('utf-8')
        elif text is None:
            text = ""
        document_id = str(uuid.uuid4())
        document_store[document_id] = text
        return RedirectResponse(url=f"/result/{document_id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

@app.get("/result/{document_id}", response_class=HTMLResponse)
async def view_result(request: Request, document_id: str, page: int = 1):
    text = document_store.get(document_id, "")
    is_duplicate = hash(text) in tfidf_calculator.document_hashes
    result = tfidf_calculator.calculate_tfidf(text)
    per_page = 50
    start = (page - 1) * per_page
    end = start + per_page
    paginated_result = result[start:end]
    total_pages = (len(result) + per_page - 1) // per_page
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": paginated_result,
        "page": page,
        "total_pages": total_pages,
        "text": text,
        "is_duplicate": is_duplicate,
        "upload_count": tfidf_calculator.total_documents,
        "document_id": document_id
    })

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})