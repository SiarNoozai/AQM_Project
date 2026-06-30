# Project Finishing Plan

## Aktueller Stand

- Frontend: React + Vite Dashboard mit kompaktem One-Screen-Layout, Demo-Fallback, Live-Analyse-Button, CSV/PDF-Export und KI-Spalte.
- Backend: FastAPI mit `yfinance`, Pandas/NumPy/SciPy, Max-Sharpe-Optimierung, Kennzahlen, Korrelationsmatrix, Effizienzgrenze, Ollama-Interpretation und regelbasiertem Fallback.
- Dokumentation: Projektplan unter `docs/projektplan-portfolio-risikoanalyse.md`, README mit lokaler Ausfuehrung und DigitalOcean-Hinweisen.
- Grenzen: Rueckfragen, Portfolio-Speicherung, Risikobeitraege, mehrere Strategien, Caching, strukturierter KI-Bericht, Tests und finale Dokumentationsartefakte sind noch nicht vollstaendig umgesetzt.

## Fehlende Funktionen

- Rueckfragenfunktion nach dem KI-Bericht.
- Lokale Speicherung von Portfolios.
- Robustere Asset-Allocation mit transparentem Metadatenstatus.
- Quantitative Risikobeitraege je Position.
- Alternative Strategien neben Max-Sharpe.
- Strukturierter KI-Bericht mit Abschnitten statt kurzer Empfehlungsliste.
- Automatisierte Tests fuer Quant-Logik und API.
- Serverseitiges Caching fuer Kursdaten.
- Finale Dokumentation fuer Architektur, Datenfluss, Testfaelle und Projektgrenzen.

## Geplante Umsetzung

1. Backend-Modelle erweitern: Metadatenstatus, Risikobeitraege, Strategien, strukturierter Report und Rueckfragen-Request/Response.
2. Quant-Schicht erweitern: Cache, Asset-Metadaten-Fallback, Risikobeitragsberechnung und defensive Strategien.
3. KI-Schicht erweitern: strukturierter Report und kontextgebundene Rueckfragen mit Ollama plus regelbasiertem Fallback.
4. Frontend erweitern: Portfolio-Speicherung per LocalStorage, Strategie-/Risikobeitragsanzeige, Report-Abschnitte und Rueckfrage-UI.
5. Tests ergaenzen: Backend-Unit-Tests und API-Smoke-Tests mit dokumentiertem Befehl.
6. Dokumentationsartefakte erstellen: `ARCHITECTURE.md`, `DATA_FLOW.md`, `TEST_CASES.md`, `FINAL_PROJECT_NOTES.md`, `PROJECT_FINAL_STATUS.md`.

## Betroffene Dateien

- `backend/models.py`
- `backend/analysis.py`
- `backend/recommendations.py`
- `backend/main.py`
- `backend/exports.py`
- `backend/pyproject.toml`
- `src/lib/api.ts`
- `src/lib/portfolioStorage.ts`
- `src/App.tsx`
- `src/styles.css`
- `README.md`
- `docs/*.md`
- `backend/tests/*.py`

## Risiken

- yfinance-Metadaten sind je nach Ticker unvollstaendig oder langsam; deshalb wird eine transparente Fallback-Klassifikation verwendet.
- Ollama ist lokal optional; die App muss ohne laufendes Ollama weiter nutzbar bleiben.
- Das One-Screen-Layout hat wenig Platz; neue UI-Elemente muessen kompakt bleiben.
- DigitalOcean kann nicht vollstaendig aus dieser lokalen Umgebung deployed werden; lokal pruefbare Build-/Start-Kommandos werden dokumentiert.

## Teststrategie

- Backend: Unit-Tests fuer Kennzahlen, Gewichtungen, Risikobeitraege, Strategien und Fehlerfaelle.
- API: TestClient-Smoke-Tests fuer Health, Analyze-Validierung und Ask-Fallback.
- Frontend: TypeScript/Vite-Build als statischer Check.
- Manuell: Live-Analyse mit Beispielportfolio, Export, Rueckfragen, Portfolio-Speicherung und 1440x900-Layout pruefen.
