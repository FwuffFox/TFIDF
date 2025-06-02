from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.tfidf import TFIDFCalculator
from typing import Optional


app = FastAPI()
tfidf_calculator = TFIDFCalculator()
templates = Jinja2Templates(directory="app/templates")

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None), page: int = Form(1)):
    try:
        if text is None and file is not None:
            text = (await file.read()).decode('utf-8')
        elif text is None:
            text = ""
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
            "upload_count": tfidf_calculator.total_documents
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})