# Meilensteinplan

## Plan

- Mockup-Prototyp mit React + Vite erstellen.
- Eingabebereich fuer Ticker und Gewichtungen bauen.
- Risiko- und Renditekennzahlen sichtbar machen.
- Performance, Korrelationen und Effizienzgrenze visualisieren.
- KI-Empfehlungsschicht als interpretierende Demo integrieren.
- Projekt so dokumentieren, dass Lastenheft, Pflichtenheft und August-Ausbau anschliessbar bleiben.

## Weighting and evaluating the plan

Fuer die erste Praesentation am 15. Juli ist ein stabiler, verstaendlicher und optisch sauberer Prototyp wichtiger als eine vollstaendige produktive Finanzdatenpipeline. Deshalb wird der Mockup-Prototyp mit deterministischen Demo-Daten umgesetzt. Die quantitative Struktur bleibt aber fachlich plausibel: Renditen, Volatilitaet, Korrelationen, Sharpe Ratio, Value at Risk und Portfoliooptimierung sind sichtbar und methodisch erklaerbar.

## Execution of the plan: result

Der aktuelle Stand ist ein interaktives Dashboard mit lokalem Quant-Backend:

- Portfolioeingabe mit Ticker, Namen und Gewichtungen
- automatische Normalisierung der Gewichte auf 100 Prozent
- KPI-Kacheln fuer erwartete Rendite, Volatilitaet, Sharpe Ratio und VaR
- normalisierte Performance-Zeitreihe
- Korrelationsmatrix als Heatmap
- Effizienzgrenze mit aktuellem und optimiertem Portfolio
- echte Kursdaten via yfinance/Yahoo Finance
- Max-Sharpe-Optimierung mit SciPy
- KI-Empfehlungsbox mit Ollama-Anbindung und regelbasiertem Fallback
- CSV- und PDF-Export fuer Bericht und Praesentation

## Evaluation of the result

Der Prototyp eignet sich fuer die erste Praesentation, weil er die Produktidee direkt bedienbar macht und bereits echte historische Daten verarbeiten kann. Der Demo-Fallback bleibt erhalten, damit die Praesentation auch ohne Internet, Backend oder Ollama stabil bleibt. Noch nicht final sind Deployment, persistente Nutzerdaten, erweitertes Backtesting und fachlich umfangreichere Optimierungsvarianten.

## Creating the new plan to perfect the original plan

- Backend-Tests fuer Quant-Berechnung und API-Fehlerfaelle ergaenzen.
- Weitere Optimierungsziele ergaenzen: Minimum-Volatilitaet, Zielrendite, Risikoparitaet.
- Eingabevalidierung im Frontend ausbauen.
- Export optisch verfeinern und optional Diagramme in den PDF-Bericht aufnehmen.
- Lokales LLM-Prompting evaluieren und Quellen-/Disclaimer-Text weiter schaerfen.
- Berichtskapitel zu Methodik, Architektur und Grenzen der historischen Analyse ausformulieren.
