# Final Project Notes

## Zweck

Das Projekt ist ein lokales Ausbildungs-MVP für historische Portfolio- und Risikoanalyse. Es verbindet eine quantitative Berechnungsschicht mit einer getrennten Interpretationsebene und einem React-Dashboard.

## Methodik

Die Berechnung arbeitet mit Schlusskursen und Periodenrenditen. Der arithmetische Erwartungswert ist das annualisierte Mittel der Periodenrenditen. Die geometrische Rendite ist die annualisierte CAGR der Kursreihe. Die Volatilität wird aus der annualisierten Kovarianzmatrix und den Gewichten berechnet; die Sharpe Ratio ist Überschussrendite geteilt durch Volatilität.

Der VaR ist ein historisches unteres Quantil der Portfolio-Periodenrenditen. Der Response weist Konfidenz, Methode `historisch` und den Frequenzhorizont in Tagen aus. Die Diversifikation wird über (N_{eff}=1/HHI) und einen auf 0 bis 100 skalierten Wert dargestellt. Der Diversifikationsquotient ergänzt diese Sicht um die Kovarianzen.

Die neutrale Vergleichsvariante nutzt Max-Sharpe, Summe der Gewichte 100 Prozent, Gewichtsobergrenze 35 Prozent und 20 Prozent Kovarianz-Schrumpfung. Die profilbezogene Empfehlung kann auf minimale Volatilität, maximale Diversifikation oder Max-Sharpe umschalten.

## Interpretation und Datenschutz

LLMs erhalten keinen Auftrag, Finanzdaten zu berechnen. Das Backend erzeugt einen begrenzten Analyse-Digest und validiert strukturierte Antworten. Bei Nichterreichbarkeit oder ungültigen Antworten wird der Regelmodus mit sichtbarem Grund verwendet. Lokale Provider verlassen das Gerät nicht; die optionale Cloud-API ist nur aktiv, wenn sie konfiguriert und ausgewählt ist.

## Erreicht

- Historische Analyse mit Demo-Fallback.
- Risiko-, Rendite-, Diversifikations- und Optimierungskennzahlen.
- Profilbasierte Empfehlungen und zwei Chat-Flows.
- Portfolio-Speicherung, CSV/PDF-Export und UI-Fehlerzustände.
- Tests, Build und aktualisierte technische Dokumentation.

## Grenzen und Weiterentwicklung

Die Anwendung ersetzt keine Anlageberatung. Datenanbieter, News-API und lokale Sprachmodelle sind externe Abhängigkeiten. Sinnvolle nächste Schritte wären echte Frontier-Berechnung, frei wählbare Frequenz/Konfidenz im Frontend, persistente Speicherung, Authentifizierung, Backtesting und Streaming.
