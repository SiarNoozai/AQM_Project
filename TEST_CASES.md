# Testfälle

## Automatisierte Ausführung

```bash
npm test
npm run build
uv run --project backend pytest backend/tests -q
```

Aktueller lokaler Stand: 9 Frontend-Tests in 5 Dateien und 30 Backend-Tests bestanden. Es bleibt eine bekannte Starlette-Warnung zur httpx-Kompatibilität; sie ist kein Testfehler.

## Backend-Abdeckung

- `test_analysis.py`: tägliche Renditen, Kennzahlen, Gewichtungsnormalisierung, Sektorgruppierung, Request-Validierung, strukturierte Regel-Empfehlung, Health-/Validierungsroute, lokale Suche und Demo-Fallback.
- `test_optimization.py`: effektive Positionsanzahl, Diversifikationswert, Max-Sharpe/minimale Volatilität/maximale Diversifikation, vollständige Investition, Gewichtsgrenzen und Kovarianz-Schrumpfung.
- `test_recommendations.py`: ungültige Kovarianz, unterschiedliche Profilziele und Regel-Fallback ohne Kovarianz.
- `test_conversation.py`: Zielerkennung für Altersvorsorge und geringes Risiko, Digest ohne Rohdaten-Ballast, echte Sharpe-Zahl in Regelantworten und Guardrails gegen fremde Ticker sowie Kauf-/Verkaufssprache.
- `test_exports.py`: UTF-8-BOM und Zeilenstruktur der CSV, PDF mit Chart und Demo-Hinweis sowie `422` für unvollständige Exportdaten.

## Frontend-Abdeckung

- Analyseaktionen bleiben bei ungültiger Gewichtungssumme deaktiviert.
- Aus der Suche übernommene Asset-Namen bleiben bei späteren Eingaben erhalten.
- Exportfehler werden vor dem Start eines Browserdownloads abgelehnt.
- Prozentformatierung und Datumsdarstellung verwenden die erwartete deutsche UI-Darstellung.
- Portfolio-Mathematik prüft Normalisierung, HHI-basierte Diversifikation und historischen VaR-Quantilzugriff.

## Manuelle Abnahme

- Start ohne Analyse: Es erscheinen keine berechneten Kennzahlen; der Startzustand erklärt den nächsten Schritt.
- Analyse mit AAPL/MSFT/SPY/AGG und gültigen Gewichten: Live-Ergebnis bei erreichbarem Yahoo Finance, sonst klar markierter Demo-Fallback.
- Gewichtssumme ungleich 100 Prozent: Hinweis und deaktivierte Analyseaktionen.
- Änderung von Ticker, Gewicht oder Zeitraum nach einer Analyse: altes Ergebnis wird als veraltet markiert; Wizard- und Chat-Auswahl bleiben erhalten.
- Suche nach einem Titel: Name aus dem Treffer bleibt im Portfolio erhalten.
- Ohne Ollama/LM Studio: Empfehlung und Rückfragen zeigen Regelmodus und Fallback-Grund.
- Zielgespräch: Freitext erzeugt bei ausreichenden Angaben einen Wizard-Vorschlag, der übernommen oder verworfen werden kann.
- Rückfragen: Antworten beziehen sich auf konkrete Analysewerte und enthalten den Disclaimer.
- Export: PDF enthält Deckblatt, Depot, Kennzahlen, Risikoanalyse, Vergleich, serverseitigen Chart, Auswertung und Methodik; CSV ist für Excel mit BOM/Semikolon vorbereitet. Bei Demo steht der Hinweis auf jeder PDF-Seite.
- Responsive UI: bei kleinen Breiten vertikales Scrollen statt horizontalem Seitenüberlauf.

## Grenzen

Ein echter Ollama-Erfolg, ein echtes DigitalOcean-Deployment und eine visuelle Browserabnahme bei mehreren festen Viewportgrößen sind umgebungsabhängig und werden durch die automatisierten Tests nicht simuliert. Yahoo-Finance-Daten können außerdem von Verfügbarkeit und Rate Limits abhängen.
