# Portfolio- und Risikoanalyse-Tool

Lokales MVP zur historischen Portfolioanalyse mit React/Vite-Frontend und FastAPI-Backend. Die Anwendung berechnet Kennzahlen aus Kursdaten, zeigt Risiken und eine nachvollziehbare historische Vergleichsvariante. Sie ist keine Anlageberatung und keine Prognosemaschine.

## Funktionsumfang

- Aktien und ETFs mit Gewichten eingeben, suchen, ergänzen, speichern und laden.
- Historische Kurse über `yfinance`/Yahoo Finance; bei nicht verfügbaren Live-Daten klar gekennzeichneter Demo-Fallback.
- Rendite (arithmetischer Erwartungswert und geometrische historische Rendite), Volatilität, Sharpe Ratio, historischer VaR mit Konfidenz und Horizont.
- Diversifikationswert über effektive Positionsanzahl, Diversifikationsquotient, Korrelations- und Kovarianzmatrix, Sektoraufteilung und Risikohinweise.
- Historische Max-Sharpe-Vergleichsvariante mit Schrumpfung der Kovarianzmatrix und konfigurierter Gewichtsobergrenze von 35 Prozent.
- Profilbezogene Zieloptimierung im KI-Workspace: maximale Diversifikation, minimale Volatilität oder Max-Sharpe mit passender Obergrenze.
- Lokales Zielgespräch und Rückfragenpanel. LM Studio/Ollama werden nur zur Textinterpretation eingesetzt; ohne erreichbaren Provider arbeitet der Regelmodus.
- CSV- und PDF-Export mit Kennzahlen, Risikoanalyse, Vergleich, Chart, KI-Auswertung, Methodik und Demo-Kennzeichnung.

## Voraussetzungen

- Node.js und npm
- Python 3.11 oder neuer
- `uv`
- Für Live-Daten Internetzugriff; für lokale KI optional Ollama oder LM Studio

## Konfiguration

Die Anwendung liest `.env` im Projektstamm und `backend/.env`. Ausgangspunkt ist [.env.example](/C:/Users/siyer/AQM%20Project/.env.example).

Für die Cloud-KI legst du eine lokale Datei `.env` im Projektstamm neben `package.json` an und trägst dort für NVIDIA NIM ein:

```env
CLOUD_API_KEY=dein_nvidia_api_key
CLOUD_BASE_URL=https://integrate.api.nvidia.com
CLOUD_MODEL=nvidia/nemotron-3-nano-30b-a3b
```

Der Schlüssel bleibt damit im Backend und wird nicht an das Frontend ausgeliefert. Niemals den Key in `src/`, in eine `VITE_`-Variable oder in Git eintragen. Nach einer Änderung den Backend-Server neu starten und im KI-Workspace `Cloud-API` auswählen.

| Variable | Zweck | Standardverhalten ohne Wert |
|---|---|---|
| `VITE_API_BASE_URL` | Basis-URL des FastAPI-Backends | Vite-Proxy bzw. gleiche Herkunft |
| `VITE_PROXY_TARGET` | internes Ziel des lokalen Vite-API-Proxys | `http://127.0.0.1:8000` |
| `CORS_ORIGINS` | erlaubte Browser-Herkünfte, kommasepariert | lokale Frontend-Adressen |
| `OLLAMA_URL` / `OLLAMA_MODEL` | Ollama-Endpunkt und Modell | Provider wird versucht; bei Fehler Regelmodus |
| `LMSTUDIO_URL` / `LMSTUDIO_URLS` / `LMSTUDIO_MODEL` | LM-Studio-Endpunkt(e) und Modell | Standardadressen auf Port 1234 werden versucht |
| `LLM_TIMEOUT` | Timeout lokaler Modellanfragen in Sekunden | 90 |
| `CLOUD_API_KEY` / `CLOUD_BASE_URL` / `CLOUD_MODEL` | optionaler OpenAI-kompatibler Cloud-Provider, z. B. NVIDIA NIM | Cloud wird übersprungen |
| `CLOUD_TIMEOUT` | Timeout der Cloud-Anfrage in Sekunden | 45 |
| `ALPHA_VANTAGE_API_KEY` | optionale News-Sentiment-Signale | News-Panel bleibt ausgeblendet |

Die früher verwendeten Variablen `OPENAI_API_KEY`, `OPENAI_BASE_URL` und `OPENAI_MODEL` bleiben als Legacy-Aliase gültig.

## Start

Gesamte Anwendung:

```bash
./start-dev.sh
```

Alternativ getrennt:

```bash
npm run dev:frontend
npm run dev:backend
```

Danach ist das Frontend unter `http://127.0.0.1:5173` und die API unter `http://127.0.0.1:8000` erreichbar. Mit Docker ist der Start ebenfalls möglich:

```bash
docker compose up --build
```

## DigitalOcean

### Droplet mit Docker Compose

Auf dem Droplet wird die Datei `.env` neben `docker-compose.yml` angelegt. Die
Cloud-Konfiguration gehört ausschließlich in den Backend-Teil:

```env
CLOUD_API_KEY=dein_nvidia_api_key
CLOUD_BASE_URL=https://integrate.api.nvidia.com
CLOUD_MODEL=nvidia/nemotron-3-nano-30b-a3b
CORS_ORIGINS=https://deine-domain.example
```

Danach startest du die Services neu:

```bash
docker compose up -d --build
```

Das Frontend ruft `/api` unter derselben Herkunft auf; Compose leitet diese
Anfragen intern an den Backend-Service weiter. Der NVIDIA-Schlüssel wird somit
nicht im Browser veröffentlicht. Für Produktion sollte zusätzlich ein Reverse
Proxy mit HTTPS vor dem Frontend stehen.

### App Platform

Für einen Backend-Service setzt du `CLOUD_API_KEY`, `CLOUD_BASE_URL` und
`CLOUD_MODEL` als verschlüsselte Runtime-Umgebungsvariablen. `CORS_ORIGINS` muss
die tatsächliche Frontend-URL enthalten, wenn Frontend und Backend auf getrennten
Domains laufen. Setze niemals `CLOUD_API_KEY` als `VITE_*`-Variable: Vite würde
sie in das ausgelieferte JavaScript einbauen.

## Tests und Build

```bash
npm test
npm run build
uv run --project backend pytest backend/tests -q
```

## API-Routen

- `GET /api/health`
- `GET /api/securities/search`
- `GET /api/system/llm-check`
- `POST /api/analyze`
- `POST /api/recommend`
- `POST /api/goal-chat`
- `POST /api/ask`
- `POST /api/export/csv`
- `POST /api/export/pdf`

## Methodik

Für Preise \(P_t\) werden Periodenrenditen \(r_t=P_t/P_{t-1}-1\) verwendet. Die arithmetische Erwartungsrendite ist das Mittel der Periodenrenditen, annualisiert mit dem Frequenzfaktor. Die geometrische Rendite ist die annualisierte Wachstumsrate der Kursreihe: \((P_{Ende}/P_{Start})^{1/Jahre}-1\). Die Volatilität ist die annualisierte Standardabweichung; die Portfolio-Volatilität wird aus \(w^TΣw\) berechnet. Die Sharpe Ratio lautet \((R_p-r_f)/σ_p\).

Der Value at Risk ist ein historisches unteres Quantil der Portfolio-Periodenrenditen bei der konfigurierten Konfidenz. Der Response nennt Methode und Horizont; bei der aktuellen Frontend-Konfiguration ist das ein Tag. Der Diversifikationswert basiert auf der effektiven Positionsanzahl \(N_{eff}=1/\sum_iw_i^2\) und wird für \(n\) Positionen auf 0 bis 100 skaliert: \((N_{eff}-1)/(n-1)·100\). Der Diversifikationsquotient ist \(\sum_iw_iσ_i/σ_p\).

Die neutrale Vergleichsvariante maximiert die historische Sharpe Ratio mit Gewichten zwischen 0 und 35 Prozent, Summe 100 Prozent, und 20 Prozent Kovarianz-Schrumpfung in Richtung durchschnittlicher Korrelation. Profilziele können stattdessen minimale Volatilität, maximale Diversifikation oder eine andere Obergrenze verwenden. Diese Ergebnisse beschreiben nur den analysierten historischen Zeitraum.

## Grenzen

Die Datenqualität und Metadaten hängen von Yahoo Finance ab. Der Cache ist pro Prozess und nicht persistent. Portfolio-Speicherung erfolgt lokal im Browser. News und Sprachmodelle sind optional. Ein echtes Deployment wird durch diese lokale Prüfung nicht belegt.
