# Final Project Notes

## Erreichte Ziele

- Echte historische Kursdaten ueber yfinance.
- Quantitative Kennzahlen: Rendite, Volatilitaet, Korrelation, Sharpe Ratio, Value at Risk.
- Max-Sharpe-Optimierung und mehrere alternative Strategien.
- Risikobeitraege je Position.
- Asset Allocation mit bekanntem, inferiertem oder unbekanntem Metadatenstatus.
- Strukturierter KI-Bericht und Rueckfragenfunktion.
- Regelbasierter Fallback bei nicht erreichbarem Ollama.
- Portfolio-Speicherung im Browser.
- CSV- und PDF-Export.
- Backend-Tests und Frontend-Build-Check.

## Nicht erreichte oder bewusst begrenzte Ziele

- Keine persistente Datenbank; Speicherung erfolgt im Browser.
- Keine professionelle Finanzdaten-API mit garantierten Metadaten; yfinance-Metadaten werden durch lokale Fallbacks ergaenzt.
- Kein echtes Production-Caching; der Cache lebt nur im Backend-Prozess.
- Kein echtes DigitalOcean Deployment aus dieser lokalen Umgebung.

## Bekannte Grenzen

- Historische Kennzahlen sind keine Prognose.
- Optimierung kann nur mit den geladenen historischen Daten arbeiten.
- Unbekannte Ticker koennen analysiert werden, aber Asset Allocation bleibt dann teilweise unbekannt.
- KI-Antworten sind Interpretationen der berechneten Daten und keine Anlageberatung.

## Rechtliche Abgrenzung

Das Tool bietet keine professionelle Anlageberatung. Es dient als Ausbildungsprojekt zur quantitativen Portfolioanalyse. Nutzer muessen eigene Entscheidungen treffen und bei Bedarf professionelle Beratung einholen.

## Moegliche Weiterentwicklung

- Persistente Speicherung in Datenbank.
- Authentifizierung und Nutzerkonten.
- Erweiterte Datenanbieter fuer Sektor-, Region- und ETF-Holdings-Daten.
- Backtesting mit Rebalancing.
- Professionelleres Reporting mit Chart-Snapshots im PDF.
