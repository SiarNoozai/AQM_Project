# Portfolio- und Risikoanalyse-Tool

Mockup-Prototyp fuer den ersten Projektmeilenstein am 15. Juli.

## Ziel

Die Anwendung zeigt, wie Privatanleger ein Portfolio aus Aktien oder ETFs eingeben, historische Kennzahlen betrachten, Portfolio-Gewichtungen vergleichen und eine KI-gestuetzte Handlungsempfehlung lesen koennen.

## Aktueller Prototyp

- React + Vite Dashboard
- FastAPI Backend fuer echte Kursdaten und Quant-Berechnung
- yfinance/Yahoo Finance als historische Datenquelle
- deterministische Demo-Kursdaten als stabiler Fallback
- Portfolio-Gewichtungen per Slider
- Kennzahlen: Rendite, Volatilitaet, Sharpe Ratio, Value at Risk
- Charts: normalisierte Performance, Korrelationsmatrix, Effizienzgrenze aus API-Daten
- Max-Sharpe-Optimierung mit SciPy
- KI-Empfehlungsbereich via Ollama, mit regelbasiertem Fallback
- PDF- und CSV-Export fuer Bericht und Praesentation

## Lokal starten

```bash
npm install
npm run dev
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:5173
```

Backend in einem zweiten Terminal starten:

```bash
uv sync
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Health-Check:

```text
http://127.0.0.1:8000/api/health
```

Optional fuer lokale KI-Empfehlungen:

```bash
ollama serve
ollama pull llama3.1
```

Wenn Ollama nicht erreichbar ist, nutzt das Backend automatisch regelbasierte Empfehlungen.

## Projektlogik

Der Prototyp trennt bewusst zwischen:

1. Daten- und Quant-Schicht
2. KI-Empfehlungsschicht
3. Praesentationsschicht

Die aktuelle Version kann echte Daten ueber das lokale Backend laden. Der Demo-Modus bleibt als Praesentations-Fallback erhalten, wenn Backend, Internet oder yfinance nicht verfuegbar sind.

## API-Ueberblick

- `GET /api/health`
- `POST /api/analyze`
- `POST /api/recommend`
- `POST /api/export/csv`
- `POST /api/export/pdf`

Die Analyse basiert auf historischen Daten. Sie ist keine Anlageberatung und keine Prognose.

## DigitalOcean App Platform

Das Backend nutzt `uv`. DigitalOcean App Platform erwartet dafuer neben `pyproject.toml`
und `uv.lock` auch eine `.python-version` Datei. Diese ist auf Python `3.11.15`
gesetzt; `runtime.txt` ist als Buildpack-Fallback ebenfalls vorhanden.

Empfohlene Backend-Komponente:

```text
Type: Web Service
Source directory: /
Build command: uv sync --frozen
Run command: uv run uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
HTTP port: 8080
```

Empfohlene Frontend-Komponente:

```text
Type: Static Site
Source directory: /
Build command: npm ci && npm run build
Output directory: dist
Environment variable: VITE_API_BASE_URL=https://<backend-app-url>
```

Wenn Frontend und Backend als getrennte App-Platform-Komponenten laufen, muss
`VITE_API_BASE_URL` auf die oeffentliche URL des Backend-Service zeigen.
