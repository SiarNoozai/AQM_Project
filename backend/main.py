from __future__ import annotations

from fastapi import FastAPI, Query

try:
    from .env_config import load_env_files
except ImportError:
    from env_config import load_env_files

load_env_files()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

try:
    from .models import AnalyzeRequest, ExportRequest, RecommendRequest, RecommendResponse, SecuritySearchResponse
except ImportError:
    from models import AnalyzeRequest, ExportRequest, RecommendRequest, RecommendResponse, SecuritySearchResponse

app = FastAPI(title="Portfolio- und Risikoanalyse API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "portfolio-risk-analysis-api"}


@app.get("/api/securities/search", response_model=SecuritySearchResponse)
def search_market_securities(
    q: str = Query("", min_length=0),
    limit: int = Query(8, ge=1, le=10),
) -> SecuritySearchResponse:
    try:
        from .search import search_securities
    except ImportError:
        from search import search_securities

    return search_securities(q, limit)


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    try:
        from .analysis import run_analysis
    except ImportError:
        from analysis import run_analysis

    return run_analysis(request)


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    try:
        from .recommendations import generate_recommendations
    except ImportError:
        from recommendations import generate_recommendations

    return await generate_recommendations(request)


@app.get("/api/system/llm-check")
async def llm_check():
    """Lokaler Hardware-Check: welche LLMs kann dieser Rechner ausfuehren?"""
    try:
        from .system_check import build_llm_check
    except ImportError:
        from system_check import build_llm_check

    return await build_llm_check()


@app.post("/api/export/csv")
def export_csv(request: ExportRequest) -> Response:
    try:
        from .exports import create_csv_export
    except ImportError:
        from exports import create_csv_export

    csv_content = create_csv_export(request.analysis, request.recommendations)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="portfolio-analyse.csv"'},
    )


@app.post("/api/export/pdf")
def export_pdf(request: ExportRequest) -> Response:
    try:
        from .exports import create_pdf_export
    except ImportError:
        from exports import create_pdf_export

    pdf_content = create_pdf_export(request.analysis, request.recommendations)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="portfolio-analyse.pdf"'},
    )

# reload-trigger
