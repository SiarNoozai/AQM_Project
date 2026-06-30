# Datenfluss

## Ablauf

```mermaid
sequenceDiagram
  participant U as Nutzer
  participant F as React Frontend
  participant B as FastAPI Backend
  participant Y as yfinance
  participant Q as Quant-Logik
  participant L as Ollama/Fallback

  U->>F: Ticker, Gewichtungen, Zeitraum
  F->>B: POST /api/analyze
  B->>Y: Kursdaten abrufen oder Cache nutzen
  B->>Q: Renditen, Kennzahlen, Risiken berechnen
  Q-->>B: Strukturierte Analyse
  B-->>F: AnalysisResponse
  F->>B: POST /api/recommend
  B->>L: Strukturierte Analyse interpretieren
  L-->>B: Bericht/Empfehlungen
  B-->>F: RecommendResponse
  U->>F: Rueckfrage
  F->>B: POST /api/ask
  B->>L: Rueckfrage + Analysekontext
  L-->>F: Antwort ohne neue Finanzdaten
```

## Strukturierte Uebergabe an die KI

Die KI erhaelt:

- Portfolio-Kennzahlen
- Asset-Liste mit Gewichtung, Rendite, Volatilitaet, Assetklasse, Sektor, Region und Risikobeitrag
- Asset Allocation
- Risikohinweise
- alternative Strategien
- optimierte Gewichtungen

## Trennung von Berechnung und Interpretation

Die Berechnung liegt vollstaendig im Backend. Die KI interpretiert nur vorhandene Daten. Dadurch bleibt die Methode nachvollziehbar: Kennzahlen entstehen regelbasiert, die KI formuliert daraus verstaendliche Texte.

## Fehlerfaelle

- Fehlende oder ungueltige Kursdaten fuehren zu nutzerfreundlichen API-Fehlern.
- Ollama-Ausfall fuehrt zum regelbasierten Fallback.
- Unbekannte Ticker-Metadaten werden als `Unknown` und `metadataStatus=unknown` markiert.
- Ungueltige Gewichtungen werden von Pydantic validiert.
