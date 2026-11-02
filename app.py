from pathlib import Path
import os
import secrets
from uuid import uuid4

from flask import Flask, redirect, render_template, request, send_file, url_for, flash
from werkzeug.utils import secure_filename

from data_model import DataStorage
from reporting import create_charts, create_pdf_report

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
CHART_DIR = BASE_DIR / "static" / "charts"

for directory in (UPLOAD_DIR, DATA_DIR, REPORT_DIR, CHART_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
storage = DataStorage()


def parse_number_list(text: str) -> list[float]:
    if not text.strip():
        return []
    separators = [";", "\n", "\t"]
    for separator in separators:
        text = text.replace(separator, ",")
    return [float(part.strip().replace(",", ".")) for part in text.split(",") if part.strip()]


@app.route("/", methods=["GET"])
def index():
    stats = storage.statistics()
    data_preview = storage.to_dataframe().head(20).to_dict(orient="records")
    charts = create_charts(storage, CHART_DIR)
    chart_urls = {key: url_for("static", filename=f"charts/{path.name}") for key, path in charts.items()}
    return render_template("index.html", stats=stats, preview=data_preview, charts=chart_urls)


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("data_file")
    if not file or file.filename == "":
        flash("Оберіть CSV або Excel файл.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        flash("Підтримуються лише CSV, XLSX або XLS файли.", "error")
        return redirect(url_for("index"))

    path = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    file.save(path)
    try:
        storage.load_from_file(path)
        storage.save_to_csv(DATA_DIR / "current_data.csv")
        flash("Дані успішно завантажено з файлу.", "success")
    except Exception as exc:
        flash(f"Помилка завантаження: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/set-data", methods=["POST"])
def set_data():
    try:
        experimental = parse_number_list(request.form.get("experimental_values", ""))
        calculated = parse_number_list(request.form.get("calculated_values", ""))
        if len(experimental) != len(calculated):
            raise ValueError("Кількість значень у двох масивах має бути однаковою")
        storage.set_from_lists(experimental, calculated)
        storage.save_to_csv(DATA_DIR / "current_data.csv")
        flash("Масиви успішно записано.", "success")
    except Exception as exc:
        flash(f"Помилка введення даних: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/add-one", methods=["POST"])
def add_one():
    try:
        experimental = float(request.form.get("experimental_one", "").replace(",", "."))
        calculated = float(request.form.get("calculated_one", "").replace(",", "."))
        storage.add_pair(experimental, calculated)
        storage.save_to_csv(DATA_DIR / "current_data.csv")
        flash("Один елемент додано до обох масивів.", "success")
    except Exception as exc:
        flash(f"Помилка додавання: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/add-many", methods=["POST"])
def add_many():
    try:
        experimental = parse_number_list(request.form.get("experimental_many", ""))
        calculated = parse_number_list(request.form.get("calculated_many", ""))
        storage.add_many_pairs(experimental, calculated)
        storage.save_to_csv(DATA_DIR / "current_data.csv")
        flash("Попарне додавання виконано.", "success")
    except Exception as exc:
        flash(f"Помилка попарного додавання: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/generate-normal", methods=["POST"])
def generate_normal():
    try:
        n = int(request.form.get("normal_n", "0"))
        exp_mean = float(request.form.get("exp_mean", "0").replace(",", "."))
        exp_std = float(request.form.get("exp_std", "1").replace(",", "."))
        calc_mean = float(request.form.get("calc_mean", "0").replace(",", "."))
        calc_std = float(request.form.get("calc_std", "1").replace(",", "."))
        storage.add_normal_random_data(n, exp_mean, exp_std, calc_mean, calc_std)
        storage.save_to_csv(DATA_DIR / "current_data.csv")
        flash("Випадкові дані з нормального розподілу додано.", "success")
    except Exception as exc:
        flash(f"Помилка генерації: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/download-csv", methods=["GET"])
def download_csv():
    path = DATA_DIR / "current_data.csv"
    storage.save_to_csv(path)
    return send_file(path, as_attachment=True, download_name="analysis_data.csv")


@app.route("/download-report", methods=["GET"])
def download_report():
    charts = create_charts(storage, CHART_DIR)
    report_path = create_pdf_report(storage, REPORT_DIR / "analysis_report.pdf", charts)
    return send_file(report_path, as_attachment=True, download_name="analysis_report.pdf")


@app.route("/clear", methods=["POST"])
def clear_data():
    storage.clear()
    storage.save_to_csv(DATA_DIR / "current_data.csv")
    flash("Дані очищено.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
