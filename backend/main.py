from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

try:
    from .analysis import run_analysis
    from .exports import create_csv_export, create_pdf_export
    from .models import AnalyzeRequest, AskRequest, AskResponse, ExportRequest, RecommendRequest, RecommendResponse
    from .recommendations import answer_question, generate_recommendations
except ImportError:
    from analysis import run_analysis
    from exports import create_csv_export, create_pdf_export
    from models import AnalyzeRequest, AskRequest, AskResponse, ExportRequest, RecommendRequest, RecommendResponse
    from recommendations import answer_question, generate_recommendations


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


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    return run_analysis(request)


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    return await generate_recommendations(request.analysis, request.model)


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    return await answer_question(request.analysis, request.question, request.model)


@app.post("/api/export/csv")
def export_csv(request: ExportRequest) -> Response:
    csv_content = create_csv_export(request.analysis, request.recommendations)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="portfolio-analyse.csv"'},
    )


@app.post("/api/export/pdf")
def export_pdf(request: ExportRequest) -> Response:
    pdf_content = create_pdf_export(request.analysis, request.recommendations)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="portfolio-analyse.pdf"'},
    )
