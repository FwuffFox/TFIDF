from pydoc import isdata
from flask import Flask, request, render_template
from app.tfidf import TFIDFCalculator, WordStat

app = Flask(__name__)
tfidf_calculator = TFIDFCalculator()

@app.post("/upload")
def upload_file():
    if 'file' not in request.files:
        return "No file in request", 400
    
    file = request.files['file']

    if file:
        try:
            text = file.read().decode('utf-8')
            is_duplicate = tfidf_calculator.is_duplicate(text)
            tfidf_result = tfidf_calculator.calculate_tfidf(text)

            return render_template("index.html", result=tfidf_result,
                                    is_duplicate=is_duplicate,
                                    upload_count=len(tfidf_calculator.document_stats))
        except Exception as e:
            return f"Error processing file: {e}", 500
    
    return "No file uploaded", 400

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)