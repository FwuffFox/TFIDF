# Lesta-Flask-tfidf

Веб-приложение для загрузки текстовых файлов и анализа их содержимого с использованием алгоритма **TF-IDF**. Интерфейс позволяет просматривать значения Term Frequency (TF) и Inverse Document Frequency (IDF) для каждого уникального слова в тексте.


```bash
# Клонируйте репозиторий
git clone https://github.com/FwuffFox/Lesta-Flask-tfidf.git
cd Lesta-Flask-tfidf

# Активация venv
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Запустите сервер
FLASK_APP=app/main.py flask run
```

Или с использованием Docker:

```bash
# Клонируйте репозиторий
git clone https://github.com/FwuffFox/Lesta-Flask-tfidf.git
cd Lesta-Flask-tfidf

# Соберите образ
docker build -t lesta-flask-tfidf .
# Запустите контейнер
docker run -p 5000:5000 lesta-flask-tfidf
```