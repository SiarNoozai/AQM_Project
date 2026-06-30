# Projektplan: KI-gestuetztes Portfolio- und Risikoanalyse-Tool

## 1. Klares Projektziel

Das Projekt entwickelt ein KI-gestuetztes Portfolio- und Risikoanalyse-Tool fuer Privatanleger. Nutzer koennen ein eigenes Portfolio aus Aktien und ETFs zusammenstellen, Gewichtungen festlegen und historische Kursdaten abrufen. Auf Basis dieser Daten berechnet die Anwendung regelbasiert zentrale finanzmathematische Kennzahlen wie Rendite, Volatilitaet, Korrelationen, Sharpe Ratio und Value at Risk. Zusaetzlich werden Diversifikation, Risikotreiber und alternative Portfoliozusammensetzungen analysiert. Die KI-Komponente interpretiert ausschliesslich die berechneten Ergebnisse und erzeugt daraus einen verstaendlichen Portfolio-Report. Die Anwendung ersetzt keine professionelle Anlageberatung, sondern dient als transparentes Analyse- und Erklaerwerkzeug. Ziel ist ein realistisch umsetzbarer Prototyp, der quantitative Methoden, Softwareentwicklung und KI-gestuetzte Ergebnisaufbereitung sinnvoll verbindet.

## 2. Abgrenzung des Projekts

| Bereich | Inhalt |
| --- | --- |
| Was die Anwendung koennen soll | Portfolioeingabe, Kursdatenabruf, Kennzahlenberechnung, Risikoanalyse, Simulation alternativer Gewichtungen, KI-Report und Export. |
| Was bewusst nicht Teil ist | Depotanbindung, Live-Trading, Steuerberatung, individuelle Finanzplanung, verbindliche Kauf- oder Verkaufsempfehlungen. |
| Warum die KI keine Anlageberatung ersetzt | Die KI kennt keine persoenliche finanzielle Situation, keine Anlageziele, keine Risikotragfaehigkeit und keine rechtlichen Rahmenbedingungen des Nutzers. |
| Rolle der KI | Sie erklaert berechnete Kennzahlen, formuliert Hinweise, macht Risiken verstaendlich und ordnet Behavioral-Finance-Aspekte ein. |
| Rolle der regelbasierten Berechnung | Sie ruft Daten ab, bereinigt Zeitreihen, berechnet Kennzahlen, erkennt Auffaelligkeiten und simuliert Alternativen reproduzierbar. |

Die zentrale Abgrenzung lautet: Die quantitative Analyse trifft keine freien Anlageentscheidungen, sondern berechnet nachvollziehbare historische Kennzahlen. Die KI uebersetzt diese Ergebnisse in verstaendliche Sprache.

## 3. Muss-Ziele

1. Nutzer koennen mindestens 3 bis 5 Aktien oder ETFs mit Gewichtungen eingeben.
2. Die Anwendung kann historische Schlusskurse ueber eine externe Datenquelle laden.
3. Das System berechnet Renditen, durchschnittliche Rendite, Volatilitaet, Korrelationen, Sharpe Ratio und Value at Risk.
4. Portfolio-Rendite und Portfolio-Risiko werden auf Basis der eingegebenen Gewichtungen berechnet.
5. Das Dashboard zeigt Kennzahlen, Performance-Verlauf, Korrelationsmatrix und Risikohinweise verstaendlich an.
6. Ein regelbasiertes Modul erkennt einfache Auffaelligkeiten wie Konzentrationsrisiken, hohe Korrelationen und hohe Volatilitaet.
7. Die KI-Komponente erhaelt strukturierte Analyseergebnisse und erstellt daraus einen neutralen Report.
8. Die Anwendung zeigt deutlich, dass es sich nicht um Anlageberatung handelt.

## 4. Kann-Ziele

1. Portfoliooptimierung nach maximaler Sharpe Ratio.
2. Vergleich mehrerer alternativer Gewichtungen.
3. Asset Allocation nach Branche, Region oder Anlageklasse.
4. Export der Analyse als PDF oder CSV.
5. Rueckfragenfunktion zu Kennzahlen, Risiken oder Simulationen.
6. Speicherung mehrerer Portfolios.
7. Erweiterte Behavioral-Finance-Hinweise.
8. Caching historischer Kursdaten zur Performance-Verbesserung.

## 5. Funktionale Anforderungen

| Bereich | Funktionale Anforderungen |
| --- | --- |
| Portfolioeingabe | Nutzer koennen Ticker, Gewichtung, Zeitraum und Datenfrequenz angeben. |
| Validierung | Gewichtungen muessen plausibel sein; ungueltige Ticker und fehlende Daten werden gemeldet. |
| Datenabruf | Historische Schlusskurse werden ueber eine Finanzdatenquelle wie Yahoo Finance geladen. |
| Datenbereinigung | Fehlende Werte werden kontrolliert behandelt, zum Beispiel durch Entfernen oder Forward-Fill. |
| Kennzahlenberechnung | Rendite, Volatilitaet, Korrelation, Kovarianz, Sharpe Ratio und VaR werden berechnet. |
| Portfolioanalyse | Gesamtportfolio wird nach Rendite, Risiko, Risikobeitrag und Diversifikation bewertet. |
| Risikoregeln | Klumpenrisiken, hohe Korrelationen, geringe Diversifikation und hohe Volatilitaet werden erkannt. |
| Simulation | Alternative Gewichtungen werden erzeugt und mit dem Ausgangsportfolio verglichen. |
| KI-Report | Die KI formuliert einen strukturierten Report auf Basis der berechneten Analyseinformationen. |
| Rueckfragen | Optional kann der Nutzer einzelne Kennzahlen oder Hinweise genauer erklaeren lassen. |
| Export | Ergebnisse koennen optional als CSV oder PDF exportiert werden. |

## 6. Nicht-funktionale Anforderungen

| Anforderung | Umsetzung |
| --- | --- |
| Nachvollziehbarkeit | Formeln und Datenquellen werden dokumentiert; KI nutzt nur strukturierte Ergebnisse. |
| Verstaendlichkeit | Kennzahlen werden mit kurzen Erklaerungen, Visualisierungen und klaren Hinweisen dargestellt. |
| Performance | MVP-Ziel sind 3 bis 10 Assets und 1 bis 5 Jahre historische Daten. |
| Datenschutz | Keine Bankzugangsdaten, keine echte Depotanbindung, keine sensiblen Finanzdaten erforderlich. |
| Fehlerbehandlung | API-Ausfaelle, ungueltige Ticker und unvollstaendige Daten werden sichtbar behandelt. |
| Transparenz | Datenquelle, Zeitraum, Berechnungsmethode und Aktualisierungszeitpunkt werden angezeigt. |
| Sicherheit | Keine geheimen API-Schluessel im Frontend; Backend validiert Eingaben. |
| Reproduzierbarkeit | Berechnungen erfolgen deterministisch auf Basis der geladenen Kursdaten. |
| Rechtliche Abgrenzung | Disclaimer stellt klar, dass keine Anlageberatung erbracht wird. |

## 7. Technische Architektur

| Komponente | Vorschlag |
| --- | --- |
| Frontend | React mit Vite oder alternativ Streamlit fuer einen schnellen Prototyp. |
| Backend | Python FastAPI fuer Datenabruf, Berechnungen, KI-Anbindung und Export. |
| Datenabruf | `yfinance` als kostenlose Datenquelle; alternativ Alpha Vantage, Twelve Data oder Polygon.io. |
| Berechnungslogik | Pandas fuer Zeitreihen, NumPy fuer Matrizen, SciPy fuer Optimierung. |
| KI-Komponente | Lokales LLM ueber Ollama oder ein API-basiertes Modell; Input nur als Analyse-JSON. |
| Datenstruktur | JSON zwischen Frontend, Backend und KI-Komponente. |
| Schnittstellen | `POST /api/analyze`, `POST /api/recommend`, `POST /api/export/csv`, `POST /api/export/pdf`, `GET /api/health`. |
| Speicherung | Fuer MVP optional; spaeter SQLite oder PostgreSQL fuer Portfolios und Analysehistorie. |

Der einfache Datenfluss:

```text
Frontend -> Backend API -> Kursdatenquelle
Frontend <- Backend API <- Quant-Modul
Backend -> KI-Komponente -> Reporttext
Frontend <- Backend API <- Report und Kennzahlen
```

Diese Architektur ist bewusst schlank. Das Frontend bleibt fuer Eingabe und Visualisierung verantwortlich, das Backend fuer Daten, Berechnung und KI-Prompting.

## 8. Datenmodell

| Objekt | Wichtige Felder |
| --- | --- |
| User | `id`, `name`, `email`, `createdAt` |
| Portfolio | `id`, `userId`, `name`, `createdAt`, `baseCurrency` |
| PortfolioPosition | `id`, `portfolioId`, `securityId`, `weight`, `quantity` |
| Security | `id`, `ticker`, `name`, `type`, `sector`, `region`, `currency` |
| HistoricalPrice | `securityId`, `date`, `closePrice`, `adjustedClosePrice`, `source` |
| PortfolioMetrics | `portfolioId`, `expectedReturn`, `volatility`, `sharpeRatio`, `valueAtRisk`, `calculatedAt` |
| AssetAllocation | `portfolioId`, `bySecurity`, `bySector`, `byRegion`, `byAssetClass` |
| RiskFinding | `id`, `portfolioId`, `type`, `severity`, `message`, `affectedAssets` |
| SimulationResult | `id`, `portfolioId`, `weights`, `expectedReturn`, `volatility`, `sharpeRatio`, `valueAtRisk` |
| AIReport | `id`, `portfolioId`, `summary`, `riskExplanation`, `recommendations`, `behavioralHints`, `disclaimer` |

Fuer das MVP kann dieses Modell zunaechst als JSON-Struktur im Backend existieren. Eine Datenbank ist erst notwendig, wenn Nutzerkonten, Speicherung oder Analysehistorien umgesetzt werden.

## 9. Berechnungslogik

| Kennzahl | Beschreibung |
| --- | --- |
| Rendite | Periodische Rendite: `(Preis_t / Preis_t-1) - 1`. Alternativ koennen logarithmische Renditen verwendet werden. |
| Durchschnittliche Rendite | Mittelwert der periodischen Renditen, bei Tagesdaten typischerweise mit 252 Handelstagen annualisiert. |
| Volatilitaet | Standardabweichung der Renditen, annualisiert durch Multiplikation mit `sqrt(252)` bei Tagesdaten. |
| Korrelation | Korrelationsmatrix der Asset-Renditen; zeigt, wie stark sich Anlagen gemeinsam bewegen. |
| Portfolio-Rendite | Gewichtete Summe der erwarteten Renditen: `sum(w_i * r_i)`. |
| Portfolio-Risiko | `sqrt(w^T * Sigma * w)`, wobei `w` der Gewichtungsvektor und `Sigma` die Kovarianzmatrix ist. |
| Sharpe Ratio | `(Portfolio-Rendite - risikofreier Zins) / Portfolio-Volatilitaet`. |
| Value at Risk | Historisch: Quantil der Portfolio-Renditen, zum Beispiel 5-Prozent-Quantil fuer 95-Prozent-Konfidenz. |

Die Berechnungen basieren auf historischen Daten und sind keine Prognose. Sie zeigen, wie sich das Portfolio im betrachteten Zeitraum verhalten hat.

## 10. KI-Integration

Die KI wird als Interpretationsebene nach der quantitativen Analyse eingebunden. Das Backend berechnet zuerst alle Kennzahlen und Risikohinweise regelbasiert. Danach erstellt es ein strukturiertes JSON mit Portfoliozusammensetzung, Kennzahlen, Asset Allocation, Risikofunden und Simulationsergebnissen. Dieses JSON wird an die KI uebergeben. Die KI darf keine Kennzahlen neu berechnen und keine freien Kauf- oder Verkaufsempfehlungen geben. Sie erklaert die Ergebnisse, weist auf Unsicherheiten hin und formuliert Behavioral-Finance-Hinweise.

Beispiel-JSON fuer die KI:

```json
{
  "portfolio": {
    "positions": [
      {"ticker": "AAPL", "weight": 0.35, "assetClass": "Stock", "sector": "Technology", "region": "USA"},
      {"ticker": "MSFT", "weight": 0.30, "assetClass": "Stock", "sector": "Technology", "region": "USA"},
      {"ticker": "SPY", "weight": 0.25, "assetClass": "ETF", "sector": "Broad Market", "region": "USA"},
      {"ticker": "AGG", "weight": 0.10, "assetClass": "ETF", "sector": "Bonds", "region": "USA"}
    ]
  },
  "metrics": {
    "expectedReturn": 0.1037,
    "volatility": 0.1248,
    "sharpeRatio": 0.83,
    "valueAtRisk95": -0.0162
  },
  "assetAllocation": {
    "byAssetClass": {"Stocks": 0.65, "ETF": 0.35},
    "bySector": {"Technology": 0.65, "Broad Market": 0.25, "Bonds": 0.10},
    "byRegion": {"USA": 1.0}
  },
  "riskFindings": [
    {"type": "concentration", "severity": "medium", "message": "Hohe Gewichtung in Technologieaktien."},
    {"type": "correlation", "severity": "medium", "message": "AAPL und MSFT weisen eine hohe Korrelation auf."},
    {"type": "behavioral", "severity": "low", "message": "Historische Renditen sollten nicht als Prognose verstanden werden."}
  ],
  "simulation": {
    "optimizedWeights": {"AAPL": 0.25, "MSFT": 0.20, "SPY": 0.40, "AGG": 0.15},
    "optimizedSharpeRatio": 0.91,
    "optimizedVolatility": 0.112
  },
  "disclaimer": "Keine Anlageberatung. Die Analyse basiert auf historischen Daten."
}
```

## 11. Beispiel fuer einen KI-Report

Das Portfolio erzielte im betrachteten Zeitraum eine historische Rendite von 10,37 Prozent pro Jahr bei einer Volatilitaet von 12,48 Prozent. Die Sharpe Ratio von 0,83 deutet darauf hin, dass das Portfolio historisch eine solide risikobereinigte Rendite erzielt hat. Auffaellig ist jedoch die starke Gewichtung einzelner Technologiepositionen, wodurch das Portfolio empfindlicher auf branchenspezifische Entwicklungen reagieren kann. Der historische Value at Risk von -1,62 Prozent beschreibt einen moeglichen Tagesverlust, der im betrachteten Zeitraum in schwachen Marktphasen erreicht oder ueberschritten werden konnte. Eine alternative Gewichtung mit hoeherem ETF- oder Anleiheanteil koennte die Schwankung reduzieren, muss aber gegen moegliche Renditeeinbussen abgewogen werden. Aus Behavioral-Finance-Sicht sollte vermieden werden, vergangene Renditen als sichere Zukunftserwartung zu interpretieren. Diese Auswertung ist keine Anlageberatung, sondern eine Erklaerung historischer Kennzahlen.

## 12. User Journey

1. Nutzer oeffnet das Dashboard.
2. Nutzer waehlt Aktien oder ETFs aus.
3. Nutzer legt Gewichtungen und Analysezeitraum fest.
4. Nutzer startet die Analyse.
5. Die Anwendung ruft historische Kursdaten ab.
6. Das Dashboard zeigt Kennzahlen, Charts und Risikohinweise.
7. Die KI erzeugt einen verstaendlichen Portfolio-Report.
8. Nutzer vergleicht das aktuelle Portfolio mit einer alternativen Gewichtung.
9. Nutzer stellt optional Rueckfragen zu Kennzahlen, Risiken oder Simulationen.

## 13. Aufgabenverteilung im Team

| Arbeitspaket | Beschreibung | Ergebnis | Abhaengigkeiten |
| --- | --- | --- | --- |
| Frontend | Dashboard, Eingabemaske, Charts und KI-Report-Box umsetzen. | Bedienbare Benutzeroberflaeche. | API-Vertrag, Designkonzept. |
| Backend/API | FastAPI-Endpunkte fuer Analyse, Empfehlung und Export bereitstellen. | Stabile REST-API. | Datenmodell, Berechnungsmodule. |
| Kursdatenabruf | Historische Preise laden und bereinigen. | Saubere Preiszeitreihen. | Tickerliste, Datenquelle. |
| Finanzkennzahlen | Renditen, Volatilitaet, Korrelationen, VaR und Sharpe Ratio berechnen. | Reproduzierbares Quant-Modul. | Kursdaten. |
| Portfolio-Simulation | Alternative Gewichtungen und Optimierung berechnen. | Vergleich aktuelles vs. alternatives Portfolio. | Kennzahlenmodul. |
| KI-Prompting | Prompt-Template und Reportstruktur definieren. | Neutraler KI-Report mit Disclaimer. | Analyse-JSON. |
| Datenmodell | Objekte und JSON-Strukturen definieren. | Dokumentiertes Datenmodell. | Anforderungen. |
| Testing | API-, Berechnungs- und UI-Smoke-Tests erstellen. | Nachweisbare Funktionspruefung. | Implementierte Module. |
| Dokumentation | Architektur, Formeln, Grenzen und Bedienung dokumentieren. | Projektbericht und README. | Alle Arbeitspakete. |
| Praesentation | Demo-Ablauf, Screenshots und Kernaussagen vorbereiten. | Vorzeigbare Projektpraesentation. | Stabiler Prototyp. |

## 14. MVP-Plan

| Version | Ziel | Inhalt |
| --- | --- | --- |
| Version 1 | Minimal lauffaehiger Prototyp | Portfolioeingabe, Demo-Daten, einfache Kennzahlen, Dashboard. |
| Version 2 | Erweiterte Analyse | Echte Kursdaten, Rendite, Volatilitaet, Korrelation, Sharpe Ratio, VaR. |
| Version 3 | KI-Report und Simulation | Risikoregeln, alternative Gewichtungen, KI-Report, Disclaimer. |
| Version 4 | Optimierung und Feinschliff | Max-Sharpe-Optimierung, Export, bessere Fehlerbehandlung, UI-Polish. |

## 15. Risiken und offene Fragen

| Risiko | Einordnung | Gegenmassnahme |
| --- | --- | --- |
| Unvollstaendige Kursdaten | Ticker koennen fehlen oder Luecken enthalten. | Validierung, Fehlermeldungen, Demo-Fallback. |
| API-Limits | Kostenlose Datenquellen koennen begrenzt sein. | Kleine Asset-Anzahl, Caching, alternative Datenquelle. |
| Falsche Kennzahleninterpretation | Nutzer koennten historische Kennzahlen als Prognose verstehen. | Erklaertexte, Disclaimer, Behavioral-Finance-Hinweise. |
| KI-Halluzinationen | KI koennte Aussagen ueber Daten hinaus formulieren. | Strikter Prompt, strukturierter Input, regelbasierter Fallback. |
| Rechtliche Abgrenzung | Risiko der Verwechslung mit Anlageberatung. | Keine Kauf-/Verkaufsempfehlungen, deutlicher Hinweis. |
| Portfoliooptimierung zu aufwendig | Optimierung kann mathematisch und technisch komplex werden. | Als Kann-Ziel behandeln, einfache Max-Sharpe-Variante nutzen. |
| Branchen- und Regionsdaten fehlen | Asset-Allocation-Daten sind nicht immer verfuegbar. | Optional manuell pflegen oder nur Wertpapiergewichtung analysieren. |
| Zeitdruck im Teamprojekt | Zu viele Features koennen das MVP gefaehrden. | Muss-/Kann-Ziele strikt trennen. |

## 16. Ergebnisdokumentation

Am Projektende sollten folgende Artefakte vorliegen:

| Artefakt | Inhalt |
| --- | --- |
| Projektskizze | Ziel, Motivation, Abgrenzung, Nutzen. |
| Technische Dokumentation | Setup, Architektur, API, Deployment. |
| Architekturdiagramm | Frontend, Backend, Datenquelle, KI-Komponente. |
| Datenflussdiagramm | Eingabe, Kursdaten, Berechnung, KI-Report, Dashboard. |
| Berechnungslogik | Formeln, Annahmen, Annualisierung, VaR-Methode. |
| KI-Prompting | Prompt-Template, strukturierter Input, Grenzen der KI. |
| Screenshots | Dashboard, Kennzahlen, Heatmap, Effizienzgrenze, KI-Report. |
| Testfaelle | Gueltige Analyse, falscher Ticker, fehlende Daten, Export, KI-Fallback. |
| Reflexion | Grenzen historischer Daten, keine Anlageberatung, moegliche Erweiterungen. |

Die Dokumentation muss klar trennen, welche Ergebnisse regelbasiert berechnet werden und welche Texte durch die KI interpretiert werden.
