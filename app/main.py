from pydoc import isdata
from flask import Flask, request, render_template
from app.tfidf import TFIDFCalculator, WordStat

app = Flask(__name__)
tfidf_calculator = TFIDFCalculator()

@app.post("/upload")
def upload_file():
    try:
        text = request.form.get("text") or request.files['file'].read().decode('utf-8')
        is_duplicate = hash(text) in tfidf_calculator.document_hashes
        result = tfidf_calculator.calculate_tfidf(text)

        # Get current page from form or default to 1
        page = int(request.form.get("page", 1))
        per_page = 50
        start = (page - 1) * per_page
        end = start + per_page

        paginated_result = result[start:end]
        total_pages = (len(result) + per_page - 1) // per_page

        return render_template("index.html",
                               result=paginated_result,
                               page=page,
                               total_pages=total_pages,
                               text=text,  # pass back original text
                               is_duplicate=is_duplicate,
                               upload_count=tfidf_calculator.total_documents)
    except Exception as e:
        return render_template("index.html", error=str(e))

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)