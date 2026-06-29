import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf



@st.cache_data # Das sorgt dafür, dass Streamlit die Daten nicht bei jedem Klick neu lädt!
def lade_kursdaten(tickers, start_datum="2020-01-01"):
    """
    Lädt historische angepasste Schlusskurse (Adj Close) für eine Liste von Tickersymbolen.
    """
    # yfinance erwartet Ticker als String mit Leerzeichen getrennt, z.B. "AAPL MSFT SPY"
    ticker_string = " ".join([t.strip() for t in tickers.split(",")])
    
    # Lade die Daten
    data = yf.download(ticker_string, start=start_datum)
    
    # Wir brauchen nur die 'Adj Close' Spalte (bereinigt um Dividenden/Splits)
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Adj Close']
    else:
        df = data[['Adj Close']]
        df.columns = [ticker_string]
        
    # Entferne Tage, an denen Kurse fehlen (z.B. Feiertage)
    df = df.dropna()
    return df


# Wenn der Nutzer Ticker in der Sidebar eingibt (z.B. AAPL, MSFT)
if st.sidebar.button("Portfolio Analysieren"):
    with st.spinner("Lade echte Marktdaten..."):
        # Echte Daten laden
        portfolio_daten = lade_kursdaten(assets)
        
        # Rendite berechnen (Tagesrendite)
        renditen = portfolio_daten.pct_change().dropna()
        
        st.success("Daten erfolgreich geladen!")
        
        # Chart mit echten normalisierten Kursen zeichnen
        st.subheader("📈 Echte Historische Entwicklung (Normalisiert auf 100)")
        normalisiert = (portfolio_daten / portfolio_daten.iloc[0]) * 100
        st.line_chart(normalisiert)


# Seiten-Konfiguration
st.set_page_config(page_title="Portfolio & Risiko AI", layout="wide")

st.title("📈 Portfolio- und Risikoanalyse-Tool")
st.markdown("Mit KI-gestützter Handlungsempfehlung für Privatanleger")

# --- SIDEBAR (Eingaben) ---
st.sidebar.header("⚙️ Portfolio konfigurieren")
assets = st.sidebar.text_input("Tickersymbole (kommasepariert)", "AAPL, MSFT, SPY")
st.sidebar.markdown("**Dummy-Gewichtung**")
st.sidebar.slider("Asset 1 (%)", 0, 100, 40)
st.sidebar.slider("Asset 2 (%)", 0, 100, 30)
st.sidebar.slider("Asset 3 (%)", 0, 100, 30)
st.sidebar.button("Portfolio Analysieren")

# --- MAIN AREA (Ergebnisse - aktuell mit Dummy-Daten) ---
st.subheader("📊 Portfolio Kennzahlen (Mockup-Daten)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ø Jährliche Rendite", "8.5 %", "+1.2 %")
col2.metric("Volatilität (Risiko)", "12.3 %", "-0.5 %")
col3.metric("Sharpe Ratio", "1.24")
col4.metric("Value at Risk (95%)", "-4.2 %")

# --- CHART (Dummy) ---
st.subheader("📈 Historische Entwicklung (Simuliert)")
# Wir generieren zufällige Daten, damit der Chart im Mockup cool aussieht
dummy_dates = pd.date_range("2023-01-01", periods=100)
dummy_data = pd.DataFrame(np.random.randn(100, 3).cumsum(axis=0), 
                          index=dummy_dates, columns=["Asset 1", "Asset 2", "Asset 3"])
st.line_chart(dummy_data)

# --- KI EMPFEHLUNG (Hardcoded für Meilenstein 1) ---
st.subheader("🤖 KI-Handlungsempfehlung")
st.info("""
**Analyse deines Portfolios:**
* **Diversifikation:** Dein Portfolio weist eine hohe Konzentration im Technologie-Sektor auf.
* **Risiko:** Die Volatilität von 12.3% ist moderat, könnte aber durch die Hinzunahme von defensiveren Werten (z.B. Anleihen-ETFs) gesenkt werden.
* **Vorschlag der Portfolio-Optimierung:** Um deine Sharpe Ratio zu maximieren, empfiehlt das mathematische Modell eine Gewichtung von 35% Asset 1, 25% Asset 2 und 40% Asset 3.
""")