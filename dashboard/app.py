import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.market_data import MarketDataEngine
from technical_analysis.indicators import TechnicalAnalysisEngine
from options.chain_analyzer import OptionChainAnalyzer
from astrology.engine import VedicAstrologyEngine
from models.combiner import CompositeMarketSynthesizer

IST = pytz.timezone("Asia/Kolkata")
st.set_page_config(page_title="NIFTY Astro-Quant Agent", layout="wide")

st.sidebar.title("Configuration")
tw = st.sidebar.slider("Technical Weight %", 10, 90, 70, 5) / 100.0
aw = 1.0 - tw

data_eng = MarketDataEngine()
tech_eng = TechnicalAnalysisEngine()
opt_eng = OptionChainAnalyzer()
astro_eng = VedicAstrologyEngine()
combiner = CompositeMarketSynthesizer(tech_weight=tw, astro_weight=aw)

quote = data_eng.fetch_live_quote("^NSEI")
ohlcv = data_eng.fetch_historical_ohlcv("^NSEI")
df_tech = tech_eng.calculate_indicators(ohlcv)
levels = tech_eng.calculate_levels(quote["high"], quote["low"], quote["previous_close"])
t_res = tech_eng.evaluate_technical_score(df_tech)

opt_data = data_eng.fetch_option_chain_data(quote["current_price"])
o_res = opt_eng.analyze_chain(opt_data)

ephem = astro_eng.calculate_ephemeris(datetime.now(IST))
a_res = astro_eng.calculate_astro_score(ephem)

synth = combiner.synthesize(t_res, o_res, a_res, levels)

st.title("📈 NIFTY 50 Technical & Astrological Analyzer")
st.caption(f"Last updated: {quote['timestamp']} | Experimental Research Model")

c1, c2, c3, c4 = st.columns(4)
c1.metric("NIFTY Spot", f"{quote['current_price']:,.2f}")
c2.metric("Technical Score", f"{t_res['score']}/100")
c3.metric("Astrology Score", f"{a_res['score']}/100")
c4.metric("Market Bias", f"{synth['emoji']} {synth['bias']}")

st.markdown("---")
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Key Support / Resistance Levels")
    st.table(pd.DataFrame([levels]).T.rename(columns={0: "Price Level"}))
    st.subheader("Scenarios")
    st.success(f"**Bullish:** {synth['scenarios']['bullish']}")
    st.error(f"**Bearish:** {synth['scenarios']['bearish']}")
    st.info(f"**Range-Bound:** {synth['scenarios']['range']}")

with col_right:
    st.subheader("Planetary Positions (Lahiri Ayanamsa)")
    st.markdown(f"**Moon Nakshatra:** {ephem['moon_nakshatra']} | **Tithi:** {ephem['tithi']}")
    st.dataframe(pd.DataFrame(ephem["positions"]).T)
    st.subheader("Option Chain Metrics")
    st.write(f"- **PCR:** {o_res['pcr']}")
    st.write(f"- **Max Pain Strike:** {o_res['max_pain']}")
    st.write(f"- **Call Resistance Wall:** {o_res['call_wall']}")
    st.write(f"- **Put Support Wall:** {o_res['put_wall']}")
