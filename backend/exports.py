from __future__ import annotations

import csv
from html import escape
from io import BytesIO, StringIO
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_csv_export(analysis: dict[str, Any], recommendations: list[str] | None = None) -> str:
    """Erzeugt einen Excel-kompatiblen, semikolongetrennten Bericht ohne Phantomfelder."""
    output = StringIO(newline="")
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    metrics = analysis.get("metrics", {})
    optimized = analysis.get("optimizedMetrics", {})

    writer.writerow(["Portfolio- und Risikoanalyse"])
    writer.writerow(["Modus", "Demo-Fallback" if analysis.get("mode") == "demo" else "Live"])
    writer.writerow(["Datenquelle", analysis.get("dataSource", "")])
    writer.writerow(["Zeitraum", f"{analysis.get('startDate', '')} bis {analysis.get('endDate', '')}"])
    writer.writerow(["Aktualisiert", analysis.get("updatedAt", "")])

    writer.writerow(["Kennzahl", "Aktuelles Portfolio", "Optimiertes Portfolio"])
    writer.writerow(["Erwartungsrendite p.a.", metrics.get("expectedReturn", ""), optimized.get("expectedReturn", "")])
    writer.writerow(["Geometrische Rendite p.a.", metrics.get("annualizedReturnGeometric", ""), optimized.get("annualizedReturnGeometric", "")])
    writer.writerow(["Volatilität p.a.", metrics.get("volatility", ""), optimized.get("volatility", "")])
    writer.writerow(["Sharpe Ratio", metrics.get("sharpeRatio", ""), optimized.get("sharpeRatio", "")])
    writer.writerow(["Value at Risk", metrics.get("valueAtRisk", ""), optimized.get("valueAtRisk", "")])
    writer.writerow(["VaR-Horizont in Tagen", metrics.get("valueAtRiskHorizonDays", ""), optimized.get("valueAtRiskHorizonDays", "")])
    writer.writerow(["VaR-Methode", metrics.get("valueAtRiskMethod", "historisch"), optimized.get("valueAtRiskMethod", "historisch")])
    writer.writerow(["Diversifikationswert", metrics.get("diversificationScore", ""), optimized.get("diversificationScore", "")])
    writer.writerow(["Effektive Positionen", metrics.get("effectiveHoldings", ""), optimized.get("effectiveHoldings", "")])
    writer.writerow(["Diversifikationsquotient", metrics.get("diversificationRatio", ""), optimized.get("diversificationRatio", "")])

    writer.writerow(["Asset", "Aktuelles Gewicht", "Optimiertes Gewicht", "Erwartungsrendite", "Geometrische Rendite p.a.", "Volatilität", "Sektor", "Instrumenttyp"])
    optimized_weights = analysis.get("optimizedWeights", [])
    for index, asset in enumerate(analysis.get("assets", [])):
        writer.writerow(
            [
                asset.get("ticker", ""),
                asset.get("weight", ""),
                optimized_weights[index] if index < len(optimized_weights) else "",
                asset.get("expectedReturn", ""),
                asset.get("annualizedReturnGeometric", ""),
                asset.get("volatility", ""),
                asset.get("sector", ""),
                asset.get("instrumentType", ""),
            ]
        )

    writer.writerow(["Branche", "Gewicht", "Positionen"])
    for sector in analysis.get("sectorAllocation", []):
        writer.writerow([sector.get("sector", ""), sector.get("weight", ""), ", ".join(sector.get("tickers", []))])

    writer.writerow(["Auffälligkeit", "Schweregrad", "Meldung"])
    for finding in analysis.get("riskFindings", []):
        writer.writerow([finding.get("type", ""), finding.get("severity", ""), finding.get("message", "")])

    writer.writerow(["Empfehlung"])
    for recommendation in recommendations or analysis.get("recommendations", []):
        writer.writerow([recommendation])

    disclaimer = str(analysis.get("disclaimer", "")).strip()
    if disclaimer:
        writer.writerow(["Hinweis", disclaimer])
    return output.getvalue()


def create_pdf_export(
    analysis: dict[str, Any],
    recommendations: list[str] | None = None,
    portfolio_name: str = "Portfolioanalyse",
) -> bytes:
    buffer = BytesIO()
    is_demo = analysis.get("mode") == "demo"
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=portfolio_name,
        leftMargin=1.45 * cm,
        rightMargin=1.45 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.45 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Tiny", parent=styles["BodyText"], fontSize=7.5, leading=9.5, textColor=colors.HexColor("#4b5d70")))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], fontSize=14, leading=17, spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name="CoverSubtitle", parent=styles["BodyText"], fontSize=11, leading=15, textColor=colors.HexColor("#41566c")))

    metrics = analysis.get("metrics", {})
    optimized = analysis.get("optimizedMetrics", {})
    recommendation_items = recommendations or analysis.get("recommendations", [])
    story: list[Any] = [
        Paragraph(escape(portfolio_name), styles["Title"]),
        Paragraph("Portfolio- und Risikoanalyse", styles["CoverSubtitle"]),
        Spacer(1, 18),
        Paragraph(
            f"Zeitraum: {escape(str(analysis.get('startDate', '')))} bis {escape(str(analysis.get('endDate', '')))}<br/>"
            f"Datenquelle: {escape(str(analysis.get('dataSource', '')))}<br/>"
            f"Erstellt: {escape(str(analysis.get('updatedAt', '')))}",
            styles["SmallBody"],
        ),
    ]
    if is_demo:
        story.extend(
            [
                Spacer(1, 16),
                Paragraph(
                    "DEMO-HINWEIS: Dieser Bericht verwendet lokale Demo-Annahmen statt Live-Marktdaten. "
                    "Er ist nur für Präsentation und Funktionsprüfung bestimmt.",
                    styles["SmallBody"],
                ),
            ]
        )
    story.extend([PageBreak(), Paragraph("Depot und Kennzahlen", styles["SectionTitle"])])

    asset_rows = [["Asset", "Gewicht", "Rendite p.a.", "Geometrisch", "Volatilität", "Sektor"]]
    for asset in analysis.get("assets", []):
        asset_rows.append(
            [
                str(asset.get("ticker", "")),
                _percent(asset.get("weight")),
                _percent(asset.get("expectedReturn")),
                _percent(asset.get("annualizedReturnGeometric")),
                _percent(asset.get("volatility")),
                str(asset.get("sector", "")),
            ]
        )
    story.append(_table(asset_rows, widths=[2.1 * cm, 2.1 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 6.0 * cm]))
    story.append(Spacer(1, 12))

    metric_rows = [
        ["Kennzahl", "Aktuell", "Vergleichsvariante"],
        ["Erwartungsrendite p.a.", _percent(metrics.get("expectedReturn")), _percent(optimized.get("expectedReturn"))],
        ["Geometrische Rendite p.a.", _percent(metrics.get("annualizedReturnGeometric")), _percent(optimized.get("annualizedReturnGeometric"))],
        ["Volatilität p.a.", _percent(metrics.get("volatility")), _percent(optimized.get("volatility"))],
        ["Sharpe Ratio", _number(metrics.get("sharpeRatio")), _number(optimized.get("sharpeRatio"))],
        ["Value at Risk", f"{_percent(metrics.get('valueAtRisk'))} / {metrics.get('valueAtRiskHorizonDays', 1)} Tag(e)", _percent(optimized.get("valueAtRisk"))],
        ["Diversifikationswert", _number(metrics.get("diversificationScore")), _number(optimized.get("diversificationScore"))],
        ["Effektive Positionen", _number(metrics.get("effectiveHoldings")), _number(optimized.get("effectiveHoldings"))],
        ["Diversifikationsquotient", _number(metrics.get("diversificationRatio")), _number(optimized.get("diversificationRatio"))],
    ]
    story.append(_table(metric_rows, widths=[7.0 * cm, 4.0 * cm, 5.8 * cm]))

    story.extend([PageBreak(), Paragraph("Risikoanalyse und Vergleich", styles["SectionTitle"])])
    findings = analysis.get("riskFindings", [])
    if findings:
        finding_rows = [["Typ", "Stufe", "Meldung"]]
        for finding in findings:
            finding_rows.append([str(finding.get("type", "")), str(finding.get("severity", "")), str(finding.get("message", ""))])
        story.append(_table(finding_rows, widths=[3.0 * cm, 2.7 * cm, 11.1 * cm]))
    else:
        story.append(Paragraph("Für diese Analyse wurden keine besonderen Auffälligkeiten abgeleitet.", styles["SmallBody"]))
    story.append(Spacer(1, 12))

    optimized_weights = analysis.get("optimizedWeights", [])
    weight_rows = [["Asset", "Aktuell", "Vergleichsvariante", "Änderung"]]
    for index, asset in enumerate(analysis.get("assets", [])):
        current = float(asset.get("weight", 0))
        target = float(optimized_weights[index]) if index < len(optimized_weights) else current
        weight_rows.append([str(asset.get("ticker", "")), _percent(current), _percent(target), _percent(target - current)])
    story.append(_table(weight_rows, widths=[4.0 * cm, 4.0 * cm, 4.8 * cm, 4.0 * cm]))

    chart = _build_performance_chart(analysis)
    if chart is not None:
        story.extend([Spacer(1, 14), Paragraph("Normalisierte Wertentwicklung", styles["SectionTitle"]), Image(chart, width=17.2 * cm, height=7.1 * cm)])

    story.extend([PageBreak(), Paragraph("KI-Auswertung und Methodik", styles["SectionTitle"])])
    if recommendation_items:
        story.append(Paragraph("Handlungsschritte", styles["Heading3"]))
        for item in recommendation_items:
            story.append(Paragraph(f"• {escape(str(item))}", styles["SmallBody"]))
    else:
        story.append(Paragraph("Für diese Analyse liegt keine zusätzliche KI-Auswertung vor.", styles["SmallBody"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Methodik", styles["Heading3"]))
    methodology = [
        "Die Erwartungsrendite ist das annualisierte arithmetische Mittel der Periodenrenditen.",
        "Die geometrische Rendite ist die annualisierte Wachstumsrate der tatsächlichen Kursreihe (CAGR).",
        "Die Volatilität ist die annualisierte Standardabweichung; die Sharpe Ratio setzt die Überschussrendite ins Verhältnis dazu.",
        f"Der Value at Risk wird als historisches Quantil mit {float(analysis.get('varConfidence', 0.95)) * 100:.0f} Prozent Konfidenz und einem Horizont von {metrics.get('valueAtRiskHorizonDays', 1)} Tag(en) berechnet.",
        "Der Diversifikationswert basiert auf der effektiven Positionsanzahl 1/HHI; der Diversifikationsquotient berücksichtigt zusätzlich Kovarianzen.",
        "Die Vergleichsvariante optimiert historische Kennzahlen mit einer Gewichtsobergrenze und ist keine Prognose.",
    ]
    for item in methodology:
        story.append(Paragraph(f"• {escape(item)}", styles["SmallBody"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(escape(str(analysis.get("disclaimer", ""))), styles["Tiny"]))

    document.build(story, onFirstPage=lambda canvas, doc: _draw_page_footer(canvas, doc, is_demo), onLaterPages=lambda canvas, doc: _draw_page_footer(canvas, doc, is_demo))
    return buffer.getvalue()


def _table(rows: list[list[str]], widths: list[float]) -> Table:
    header_style = ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9,
        textColor=colors.HexColor("#17202e"),
    )
    body_style = ParagraphStyle(name="TableBody", fontName="Helvetica", fontSize=7.6, leading=9)
    paragraph_rows = [
        [Paragraph(escape(str(cell)), header_style if row_index == 0 else body_style) for cell in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(paragraph_rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f4f1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17202e")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce3eb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_performance_chart(analysis: dict[str, Any]) -> BytesIO | None:
    performance = [point for point in analysis.get("performance", []) if isinstance(point, dict)]
    if len(performance) < 2:
        return None
    labels = [str(point.get("month") or point.get("date") or index) for index, point in enumerate(performance)]
    figure, axis = plt.subplots(figsize=(8.2, 3.2), dpi=150)
    for key, label, color, width in (("portfolio", "Portfolio", "#0b3b63", 2.2), ("optimized", "Vergleichsvariante", "#0f766e", 1.8)):
        values = [point.get(key) for point in performance]
        if all(isinstance(value, (int, float)) for value in values):
            axis.plot(labels, values, label=label, color=color, linewidth=width)
    axis.set_ylabel("Index (Start = 100)")
    axis.grid(True, alpha=0.25)
    axis.legend(frameon=False, loc="upper left")
    tick_step = max(1, len(labels) // 8)
    axis.set_xticks(range(0, len(labels), tick_step))
    axis.set_xticklabels(labels[::tick_step], rotation=30, ha="right", fontsize=7)
    figure.tight_layout()
    image = BytesIO()
    figure.savefig(image, format="png", bbox_inches="tight")
    plt.close(figure)
    image.seek(0)
    return image


def _draw_page_footer(canvas: Any, document: Any, is_demo: bool) -> None:
    canvas.saveState()
    if is_demo:
        canvas.setSubject("DEMO-HINWEIS: lokale Demo-Annahmen statt Live-Daten")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#607286"))
    canvas.drawString(document.leftMargin, 0.8 * cm, "Portfolio- und Risikoanalyse")
    canvas.drawRightString(A4[0] - document.rightMargin, 0.8 * cm, f"Seite {document.page}")
    if is_demo:
        canvas.setFillColor(colors.HexColor("#a33629"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(A4[0] - document.rightMargin, A4[1] - 0.95 * cm, "DEMO — keine Live-Daten")
    canvas.restoreState()


def _percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value) * 100:.2f} %"
    return ""


def _number(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return ""
