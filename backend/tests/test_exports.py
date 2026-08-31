from __future__ import annotations

from fastapi.testclient import TestClient

from backend.analysis import MarketDataUnavailable, run_analysis
from backend.exports import create_csv_export, create_pdf_export
from backend.main import app
from backend.models import AnalyzeRequest


def _analysis(monkeypatch):
    request = AnalyzeRequest(
        tickers=["AAPL", "MSFT", "SPY", "AGG"],
        weights=[35, 30, 25, 10],
        startDate="2021-01-01",
        endDate="2024-01-01",
        frequency="1d",
        riskFreeRate=0.025,
        varConfidence=0.95,
    )
    monkeypatch.setattr(
        "backend.analysis._download_prices",
        lambda _: (_ for _ in ()).throw(MarketDataUnavailable("offline")),
    )
    return run_analysis(request).model_dump(by_alias=True)


def test_csv_has_bom_and_no_empty_rows(monkeypatch) -> None:
    content = create_csv_export(_analysis(monkeypatch))

    assert content.startswith("\ufeff")
    assert all(any(cell.strip() for cell in row.split(";")) for row in content.lstrip("\ufeff").splitlines())


def test_pdf_contains_demo_notice_and_chart(monkeypatch) -> None:
    content = create_pdf_export(_analysis(monkeypatch), portfolio_name="Demo Portfolio")

    assert content.startswith(b"%PDF")
    assert len(content) > 10_000
    assert b"DEMO" in content


def test_incomplete_export_request_returns_422() -> None:
    client = TestClient(app)

    response = client.post("/api/export/pdf", json={"analysis": {}})

    assert response.status_code == 422
