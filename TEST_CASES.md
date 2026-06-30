# Testfaelle

## Automatisierte Tests

Ausfuehrung:

```bash
uv run --project backend pytest backend/tests
npm run build
```

## Unit-Testfaelle

- Renditeberechnung aus Tageskursen.
- Normalisierung von Portfolio-Gewichtungen.
- Rendite, Volatilitaet, Sharpe Ratio und Value at Risk.
- Risikobeitraege je Position und Summe der prozentualen Beitraege.
- Alternative Strategien mit Gewichtssumme 100 Prozent.

## API-Testfaelle

- `GET /api/health` liefert Status 200.
- `POST /api/analyze` lehnt falsche Gewichtungs-/Ticker-Struktur mit 422 ab.
- `POST /api/ask` liefert bei Ollama-Ausfall eine regelbasierte Antwort mit Disclaimer.

## UI-Testfaelle

- Portfolio aktualisieren startet Live-Analyse.
- Fehler werden sichtbar angezeigt.
- CSV/PDF-Export ist erst nach Live-Analyse aktiv.
- Portfolio kann gespeichert, geladen, ueberschrieben und geloescht werden.
- Rueckfragebox ist erst nach Live-Analyse nutzbar.
- Mobile Ansicht darf vertikal scrollen, aber nicht horizontal ueberlaufen.

## Manuelle Testfaelle

- Beispielportfolio: AAPL, MSFT, SPY, AGG.
- Ungueltiger Ticker, zum Beispiel `INVALID123`.
- Gewichtungssumme ungleich 100 Prozent.
- Ollama nicht gestartet: Fallback muss erscheinen.
- Wiederholte gleiche Analyse: Backend nutzt Cache.

## Bekannte Testgrenzen

Ein echtes DigitalOcean Deployment wurde lokal nicht ausgefuehrt. Dokumentiert sind Build- und Startbefehle sowie die benoetigten Environment Variables.
