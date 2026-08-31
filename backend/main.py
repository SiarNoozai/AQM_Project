from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .env_config import load_env_files

load_env_files()
from .analysis import run_analysis
from .conversation import answer_question, generate_goal_chat_reply
from .exports import create_csv_export, create_pdf_export
from .models import (
    AnalyzeRequest,
    AnalysisResponse,
    AskRequest,
    AskResponse,
    ExportRequest,
    GoalChatRequest,
    GoalChatResponse,
    RecommendRequest,
    RecommendResponse,
    SecuritySearchResponse,
)
from .recommendations import generate_recommendations
from .search import search_securities
from .system_check import build_llm_check

app = FastAPI(title="Portfolio- und Risikoanalyse API", version="0.1.0")


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return origins or ["http://127.0.0.1:5173", "http://localhost:5173"]


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Verbirgt interne Details und liefert eine stabile API-Fehlerform."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Ein unerwarteter Serverfehler ist aufgetreten. Bitte versuche es erneut."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_CHAT_RATE_LIMIT = 20
_CHAT_WINDOW_SECONDS = 60.0
_chat_requests: dict[str, list[float]] = {}


def _enforce_chat_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [stamp for stamp in _chat_requests.get(client_ip, []) if now - stamp < _CHAT_WINDOW_SECONDS]
    if len(recent) >= _CHAT_RATE_LIMIT:
        _chat_requests[client_ip] = recent
        raise HTTPException(status_code=429, detail="Zu viele Chat-Anfragen. Bitte warte eine Minute.")
    recent.append(now)
    _chat_requests[client_ip] = recent


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "portfolio-risk-analysis-api"}


@app.get("/api/securities/search", response_model=SecuritySearchResponse)
def search_market_securities(
    q: str = Query("", min_length=0),
    limit: int = Query(8, ge=1, le=10),
) -> SecuritySearchResponse:
    return search_securities(q, limit)


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    return run_analysis(request)


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    return await generate_recommendations(request)


@app.post("/api/goal-chat", response_model=GoalChatResponse)
async def goal_chat(request: GoalChatRequest, http_request: Request) -> GoalChatResponse:
    _enforce_chat_rate_limit(http_request)
    return await generate_goal_chat_reply(request)


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest, http_request: Request) -> AskResponse:
    _enforce_chat_rate_limit(http_request)
    return await answer_question(request)


@app.get("/api/system/llm-check")
async def llm_check():
    """Lokaler Hardware-Check: welche LLMs kann dieser Rechner ausfuehren?"""
    return await build_llm_check()


@app.post("/api/export/csv")
def export_csv(request: ExportRequest) -> Response:
    csv_content = create_csv_export(request.analysis.model_dump(by_alias=True), request.recommendations)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="portfolio-analyse.csv"'},
    )


@app.post("/api/export/pdf")
def export_pdf(request: ExportRequest) -> Response:
    pdf_content = create_pdf_export(
        request.analysis.model_dump(by_alias=True),
        request.recommendations,
        request.portfolio_name,
    )
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="portfolio-analyse.pdf"'},
    )

# reload-trigger
