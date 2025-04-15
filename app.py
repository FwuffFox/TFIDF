from flask import Flask, request, render_template
from tfidf import TFIDFCalculator, WordStat
import tfidf

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
            tfidf_result = tfidf_calculator.calculate_tfidf(text)
            return render_template("index.html", result=tfidf_result)
        except Exception as e:
            return f"Error processing file: {e}", 500
    
    return "No file uploaded", 400

@app.route("/")
def index():
    return render_template("index.html")