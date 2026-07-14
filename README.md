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
- KI-Empfehlungsbereich via LM Studio oder Ollama (beide lokal), mit regelbasiertem Fallback
- Lokaler LLM-Kompatibilitaets-Check: zeigt, welche Sprachmodelle die eigene Hardware ausfuehren kann (inspiriert von LLMcalc, github.com/Raskoll2/LLMcalc)
- PDF- und CSV-Export fuer Bericht und Praesentation

## Mit Docker starten (empfohlen fuer Windows + macOS)

Identische Umgebung auf jedem Rechner - kein Venv-, Pfad- oder Node-Setup noetig:

```bash
docker compose up --build
```

Danach: Frontend auf http://127.0.0.1:5173, Backend auf http://127.0.0.1:8000.
Quellcode ist per Volume eingebunden - Aenderungen laden automatisch neu (Vite HMR + uvicorn --reload).

LM Studio und Ollama laufen auf dem Host und werden aus den Containern ueber
`host.docker.internal` erreicht. Eigene Adresse per Umgebungsvariable:

```bash
LMSTUDIO_URL=http://host.docker.internal:1234 docker compose up
```

## Lokal starten

Am einfachsten startest du alles ueber genau eine Datei:

```bash
./start-dev.sh
```

Alternativ auf macOS per Doppelklick:

```text
start-dev.command
```

Oder per npm:

```bash
npm run dev
```

Das startet Frontend und Backend gemeinsam und beendet beide auch wieder zusammen mit `Ctrl + C`.

Wenn du nur das Frontend starten willst:

```bash
npm run dev:frontend
```

Wenn du nur das Backend starten willst:

```bash
npm run dev:backend
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:5173
```

Manuell brauchst du Frontend und Backend nur noch selten getrennt:

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Falls `uv` auf deinem Rechner noch nicht installiert ist:

```bash
python3 -m pip install uv
```

Health-Check:

```text
http://127.0.0.1:8000/api/health
```

Optional fuer lokale KI-Empfehlungen (eine der beiden Varianten):

LM Studio (empfohlen): App starten, ein Modell laden (z. B. Dolphin 2.9 Llama3 8B Q4_K_M)
und im Developer-Tab den lokalen Server starten (Port 1234).

```bash
ollama serve
ollama pull llama3.1
```

Provider-Kette: LM Studio -> Ollama -> regelbasierter Fallback. Wenn kein lokales
Sprachmodell erreichbar ist, nutzt das Backend automatisch regelbasierte Empfehlungen.

## Projektlogik

Der Prototyp trennt bewusst zwischen:

1. Daten- und Quant-Schicht
2. KI-Empfehlungsschicht
3. Praesentationsschicht

Die aktuelle Version kann echte Daten ueber das lokale Backend laden. Der Demo-Modus bleibt als Praesentations-Fallback erhalten, wenn Backend, Internet oder yfinance nicht verfuegbar sind.

## API-Ueberblick

- `GET /api/health`
- `GET /api/securities/search`
- `GET /api/system/llm-check`
- `POST /api/analyze`
- `POST /api/recommend`
- `POST /api/export/csv`
- `POST /api/export/pdf`

Die Analyse basiert auf historischen Daten. Sie ist keine Anlageberatung und keine Prognose.
