from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from data_model import DataStorage


def create_charts(storage: DataStorage, output_dir: str | Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exp = np.array(storage.experimental, dtype=float)
    calc = np.array(storage.calculated, dtype=float)
    charts: dict[str, Path] = {}

    if exp.size == 0 and calc.size == 0:
        return charts

    line_path = output_path / "line_chart.png"
    plt.figure(figsize=(8, 4.5))
    if exp.size:
        plt.plot(range(1, exp.size + 1), exp, marker="o", label="Experimental")
    if calc.size:
        plt.plot(range(1, calc.size + 1), calc, marker="o", label="Calculated")
    plt.title("Порівняння експериментальних і розрахункових даних")
    plt.xlabel("Номер спостереження")
    plt.ylabel("Значення")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(line_path, dpi=150)
    plt.close()
    charts["line"] = line_path

    histogram_path = output_path / "histogram.png"
    plt.figure(figsize=(8, 4.5))
    if exp.size:
        plt.hist(exp, bins=min(15, max(3, exp.size // 2)), alpha=0.6, label="Experimental")
    if calc.size:
        plt.hist(calc, bins=min(15, max(3, calc.size // 2)), alpha=0.6, label="Calculated")
    plt.title("Гістограма розподілу значень")
    plt.xlabel("Значення")
    plt.ylabel("Частота")
    plt.legend()
    plt.tight_layout()
    plt.savefig(histogram_path, dpi=150)
    plt.close()
    charts["histogram"] = histogram_path

    min_len = min(exp.size, calc.size)
    if min_len:
        scatter_path = output_path / "scatter.png"
        plt.figure(figsize=(6, 6))
        plt.scatter(exp[:min_len], calc[:min_len])
        plt.title("Діаграма розсіювання")
        plt.xlabel("Experimental")
        plt.ylabel("Calculated")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(scatter_path, dpi=150)
        plt.close()
        charts["scatter"] = scatter_path

    return charts


def create_pdf_report(storage: DataStorage, output_file: str | Path, charts: dict[str, Path]) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(str(output_path), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Data Analysis Report", styles["Title"]))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    stats = storage.statistics()
    table_data = [["Array", "Count", "Mean", "Median", "Variance", "Std", "Min", "Max"]]
    for name, values in stats.items():
        table_data.append([
            name,
            values["count"],
            _fmt(values["mean"]),
            _fmt(values["median"]),
            _fmt(values["variance"]),
            _fmt(values["std"]),
            _fmt(values["min"]),
            _fmt(values["max"]),
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 16))

    for title, key in [
        ("Line chart", "line"),
        ("Histogram", "histogram"),
        ("Scatter diagram", "scatter"),
    ]:
        if key in charts:
            elements.append(Paragraph(title, styles["Heading2"]))
            elements.append(Image(str(charts[key]), width=450, height=250))
            elements.append(Spacer(1, 12))

    document.build(elements)
    return output_path


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.4f}"
