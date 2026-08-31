# Project Final Status

## Umgesetzt

- React/Vite-Dashboard mit Portfolio-Builder, Suche, Gewichten, Zeitraumwahl und sichtbarer Gewichtungssumme.
- Zustandslogik für veraltete Analysen: Änderungen am Portfolio löschen nicht die Wizard-Auswahl, markieren das Ergebnis aber als erneuerungsbedürftig.
- FastAPI-Analyse mit Live-Kursdaten über yfinance und transparentem Demo-Fallback.
- Arithmetische und geometrische Rendite, annualisierte Volatilität, Sharpe Ratio, historischer VaR mit Methode/Horizont, effektive Positionsanzahl, Diversifikationswert und Diversifikationsquotient.
- Korrelations-/Kovarianzmatrix, Sektoraufteilung, Risikobefunde sowie historische Max-Sharpe-Vergleichsvariante mit Obergrenze.
- Anlegerprofil und Ziel beeinflussen die profilbezogene Gewichtungsempfehlung durch unterschiedliche Optimierungsziele und Obergrenzen.
- KI-Empfehlung mit LM Studio, Ollama und optionaler Cloud-API; strukturierte Validierung sowie sichtbarer Regel-Fallback mit Grund und getesteten Backends.
- Zielgespräch unter `POST /api/goal-chat` und Rückfragen unter `POST /api/ask`, jeweils mit begrenztem Verlauf, Disclaimer und Guardrails.
- Portfolio-Speicherung im Browser-LocalStorage.
- CSV-Export mit BOM/Semikolon und PDF-Export mit Deckblatt, Tabellen, serverseitigem Performance-Chart, KI-Auswertung, Methodik und seitenweiser Demo-Kennzeichnung.
- Komponentenaufteilung für wiederverwendbare KPI-, Heatmap-, Sektor-, Skeleton- und Chat-Ansichten.
- Backend- und Frontend-Testsetup sowie `CLAUDE.md` mit Projektregeln.

## Bewusst nicht umgesetzt

- Keine echte Effizienzgrenze: Das frühere `frontier`-Payload wurde entfernt. Eine echte Frontier ist als optionale spätere Aufgabe offen.
- Kein Streaming für Chatantworten.
- Frequenz, Zinssatz und VaR-Konfidenz sind im Backend modelliert, werden im aktuellen Frontend aber nicht frei konfiguriert.
- Keine Datenbank, Authentifizierung oder Nutzerkonten.
- Kein persistenter Multi-Worker-Cache.
- Kein echtes DigitalOcean-Deployment aus dieser lokalen Umgebung.

## Bekannte Grenzen

- Live-Daten und Metadaten hängen von Yahoo Finance ab; bei Fehlern kann die Analyse in den Demo-Modus wechseln.
- Der Demo-Modus nutzt lokale Annahmen und ist keine Live-Marktanalyse.
- Optimierung und Empfehlungen sind historische Vergleichsrechnungen, keine Prognosen oder Anlageberatung.
- News-Signale sind nur mit `ALPHA_VANTAGE_API_KEY` verfügbar.
- Ein erreichbares Ollama-/LM-Studio-Modell wird nicht in jedem Testlauf vorausgesetzt; ohne Provider greift der Regelmodus.

## Verifikation

```text
npm test                         9 Tests bestanden
npm run build                    erfolgreich
uv run --project backend pytest backend/tests -q
                                30 Tests bestanden, 1 Deprecation-Warnung
```

Die vollständige Abnahmeliste mit manuellen, umgebungsabhängigen Punkten steht in `TEST_CASES.md`. Diese Statusdatei enthält keine lokalen Screenshotpfade und behauptet kein Deployment, das nicht ausgeführt wurde.
