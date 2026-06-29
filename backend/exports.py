from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_csv_export(analysis: dict[str, Any], recommendations: list[str] | None = None) -> str:
    output = StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow(["Portfolio- und Risikoanalyse"])
    writer.writerow(["Datenquelle", analysis.get("dataSource", "")])
    writer.writerow(["Aktualisiert", analysis.get("updatedAt", "")])
    writer.writerow([])

    metrics = analysis.get("metrics", {})
    writer.writerow(["Kennzahl", "Aktuelles Portfolio", "Optimiertes Portfolio"])
    optimized = analysis.get("optimizedMetrics", {})
    writer.writerow(["Rendite", metrics.get("expectedReturn", ""), optimized.get("expectedReturn", "")])
    writer.writerow(["Volatilitaet", metrics.get("volatility", ""), optimized.get("volatility", "")])
    writer.writerow(["Sharpe Ratio", metrics.get("sharpeRatio", ""), optimized.get("sharpeRatio", "")])
    writer.writerow(["Value at Risk", metrics.get("valueAtRisk", ""), optimized.get("valueAtRisk", "")])
    writer.writerow([])

    writer.writerow(["Asset", "Aktuelles Gewicht", "Optimiertes Gewicht", "Rendite", "Volatilitaet"])
    optimized_weights = analysis.get("optimizedWeights", [])
    for index, asset in enumerate(analysis.get("assets", [])):
        writer.writerow(
            [
                asset.get("ticker", ""),
                asset.get("weight", ""),
                optimized_weights[index] if index < len(optimized_weights) else "",
                asset.get("expectedReturn", ""),
                asset.get("volatility", ""),
            ]
        )
    writer.writerow([])

    writer.writerow(["Empfehlungen"])
    for recommendation in recommendations or analysis.get("recommendations", []):
        writer.writerow([recommendation])

    return output.getvalue()


def create_pdf_export(analysis: dict[str, Any], recommendations: list[str] | None = None) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title="Portfolio- und Risikoanalyse")
    styles = getSampleStyleSheet()
    story: list[Any] = []

    metrics = analysis.get("metrics", {})
    optimized = analysis.get("optimizedMetrics", {})
    story.append(Paragraph("Portfolio- und Risikoanalyse", styles["Title"]))
    story.append(Paragraph("Bericht fuer den Prototyp eines Risikoanalyse-Dashboards.", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Datenquelle: {analysis.get('dataSource', '')}", styles["BodyText"]))
    story.append(Paragraph(f"Aktualisiert: {analysis.get('updatedAt', '')}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    metric_table = Table(
        [
            ["Kennzahl", "Aktuell", "Optimiert"],
            ["Rendite", _percent(metrics.get("expectedReturn")), _percent(optimized.get("expectedReturn"))],
            ["Volatilitaet", _percent(metrics.get("volatility")), _percent(optimized.get("volatility"))],
            ["Sharpe Ratio", _number(metrics.get("sharpeRatio")), _number(optimized.get("sharpeRatio"))],
            ["Value at Risk", _percent(metrics.get("valueAtRisk")), _percent(optimized.get("valueAtRisk"))],
        ],
        hAlign="LEFT",
    )
    metric_table.setStyle(_table_style())
    story.append(metric_table)
    story.append(Spacer(1, 14))

    optimized_weights = analysis.get("optimizedWeights", [])
    asset_rows = [["Asset", "Aktuell", "Optimiert", "Rendite", "Volatilitaet"]]
    for index, asset in enumerate(analysis.get("assets", [])):
        asset_rows.append(
            [
                asset.get("ticker", ""),
                _percent(asset.get("weight")),
                _percent(optimized_weights[index] if index < len(optimized_weights) else None),
                _percent(asset.get("expectedReturn")),
                _percent(asset.get("volatility")),
            ]
        )
    asset_table = Table(asset_rows, hAlign="LEFT")
    asset_table.setStyle(_table_style())
    story.append(asset_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("KI-/Regelbasierte Interpretation", styles["Heading2"]))
    for recommendation in recommendations or analysis.get("recommendations", []):
        story.append(Paragraph(f"- {recommendation}", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(str(analysis.get("disclaimer", "")), styles["Italic"]))

    document.build(story)
    return buffer.getvalue()


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f4f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17202e")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce3eb")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]
    )


def _percent(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value * 100:.2f} %"
    return ""


def _number(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}"
    return ""
