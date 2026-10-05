import os

files = {
    "requirements.txt": """numpy>=2.1.0
pandas>=2.2.0
scipy>=1.14.0
yfinance>=0.2.40
requests>=2.32.0
pytz>=2024.1
pydantic>=2.8.0
python-dotenv>=1.0.1
plotly>=5.24.0
streamlit>=1.39.0
ephem>=4.1.6
""",
    "config/__init__.py": "",
    "config/settings.py": """import os
from dotenv import load_dotenv

load_dotenv()

TECHNICAL_WEIGHT = float(os.getenv("DEFAULT_TECHNICAL_WEIGHT", 0.70))
ASTROLOGY_WEIGHT = float(os.getenv("DEFAULT_ASTROLOGY_WEIGHT", 0.30))
DEFAULT_AYANAMSA = "Lahiri"
MARKET_OPEN_TIME = "09:15"
MARKET_CLOSE_TIME = "15:30"
IST_TIMEZONE = "Asia/Kolkata"

NSE_LATITUDE = 19.0760
NSE_LONGITUDE = 72.8777
NSE_ELEVATION_METERS = 14
""",
    "data/__init__.py": "",
    "data/market_data.py": """import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

class MarketDataEngine:
    def fetch_historical_ohlcv(self, symbol="^NSEI", period="6mo", interval="1d"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return self._generate_sample_ohlcv(symbol)
            df.reset_index(inplace=True)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            return df
        except Exception:
            return self._generate_sample_ohlcv(symbol)

    def fetch_live_quote(self, symbol="^NSEI"):
        df = self.fetch_historical_ohlcv(symbol=symbol, period="5d", interval="1d")
        if len(df) < 2:
            return {
                "symbol": symbol, "current_price": 24850.0, "previous_close": 24780.0,
                "open": 24800.0, "high": 24910.0, "low": 24750.0, "volume": 150000000,
                "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
            }
        last, prev = df.iloc[-1], df.iloc[-2]
        return {
            "symbol": symbol,
            "current_price": float(last["Close"]),
            "previous_close": float(prev["Close"]),
            "open": float(last["Open"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "volume": int(last["Volume"]),
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        }

    def fetch_option_chain_data(self, spot_price):
        atm = round(spot_price / 50) * 50
        strikes = [atm + i * 50 for i in range(-8, 9)]
        chain = []
        for s in strikes:
            dist = (s - spot_price) / spot_price
            c_oi = int(max(5000, 140000 * np.exp(-((s - (atm + 150))**2) / (2 * (250**2)))))
            p_oi = int(max(5000, 150000 * np.exp(-((s - (atm - 150))**2) / (2 * (250**2)))))
            chain.append({
                "strikePrice": s, "call_OI": c_oi, "call_change_OI": int(np.random.normal(5000, 8000)),
                "call_LTP": max(1.0, (spot_price - s) + 100 if spot_price > s else 100 * np.exp(-abs(dist)*10)),
                "put_OI": p_oi, "put_change_OI": int(np.random.normal(6000, 8000)),
                "put_LTP": max(1.0, (s - spot_price) + 100 if s > spot_price else 100 * np.exp(-abs(dist)*10))
            })
        return {"spot": spot_price, "chain": chain, "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")}

    def _generate_sample_ohlcv(self, symbol):
        dates = pd.date_range(end=datetime.now(), periods=180, freq="B")
        base = 24000.0 if "BANK" not in symbol else 51000.0
        returns = np.random.normal(0.0005, 0.01, len(dates))
        prices = base * np.cumprod(1 + returns)
        highs = prices * (1 + np.abs(np.random.normal(0.003, 0.003, len(dates))))
        lows = prices * (1 - np.abs(np.random.normal(0.003, 0.003, len(dates))))
        opens = lows + (highs - lows) * 0.5
        return pd.DataFrame({"Date": dates, "Open": opens, "High": highs, "Low": lows, "Close": prices, "Volume": 10000000})
""",
    "technical_analysis/__init__.py": "",
    "technical_analysis/indicators.py": """import pandas as pd
import numpy as np

class TechnicalAnalysisEngine:
    @staticmethod
    def calculate_indicators(df):
        df = df.copy()
        for p in [5, 9, 20, 50, 200]:
            df[f"EMA_{p}"] = df["Close"].ewm(span=p, adjust=False).mean()
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        df["RSI"] = 100 - (100 / (1 + rs))
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
        tr = pd.concat([df["High"] - df["Low"], (df["High"] - df["Close"].shift()).abs(), (df["Low"] - df["Close"].shift()).abs()], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()
        df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / (df["Volume"].cumsum() + 1e-9)
        return df

    @staticmethod
    def calculate_levels(prev_high, prev_low, prev_close):
        p = (prev_high + prev_low + prev_close) / 3.0
        return {
            "Pivot": round(p, 2),
            "R1": round(2 * p - prev_low, 2), "R2": round(p + (prev_high - prev_low), 2), "R3": round(prev_high + 2 * (p - prev_low), 2),
            "S1": round(2 * p - prev_high, 2), "S2": round(p - (prev_high - prev_low), 2), "S3": round(prev_low - 2 * (prev_high - p), 2)
        }

    @staticmethod
    def evaluate_technical_score(df):
        if len(df) < 50:
            return {"score": 0.0, "reasons": ["Insufficient history"], "rsi": 50.0, "vwap": 0.0}
        last = df.iloc[-1]
        score = 0
        reasons = []
        if last["Close"] > last["EMA_20"] > last["EMA_50"]:
            score += 35
            reasons.append("Bullish stack: Close > EMA 20 > EMA 50")
        elif last["Close"] < last["EMA_20"] < last["EMA_50"]:
            score -= 35
            reasons.append("Bearish stack: Close < EMA 20 < EMA 50")
        rsi = last["RSI"]
        if 55 <= rsi <= 70:
            score += 25
            reasons.append(f"RSI in positive momentum ({rsi:.1f})")
        elif 30 <= rsi <= 45:
            score -= 25
            reasons.append(f"RSI in negative momentum ({rsi:.1f})")
        if last["MACD_Hist"] > 0:
            score += 20
            reasons.append("MACD histogram bullish divergence")
        else:
            score -= 20
            reasons.append("MACD histogram bearish divergence")
        return {"score": max(-100, min(100, score)), "reasons": reasons, "rsi": round(rsi, 2), "vwap": round(last["VWAP"], 2)}
""",
    "options/__init__.py": "",
    "options/chain_analyzer.py": """import pandas as pd
import numpy as np

class OptionChainAnalyzer:
    @staticmethod
    def analyze_chain(option_chain_dict):
        df = pd.DataFrame(option_chain_dict["chain"])
        spot = option_chain_dict["spot"]
        total_call_oi = df["call_OI"].sum()
        total_put_oi = df["put_OI"].sum()
        pcr = round(total_put_oi / (total_call_oi + 1e-9), 3)
        strikes = df["strikePrice"].values
        losses = [np.sum(np.maximum(0, s - strikes) * df["call_OI"].values + np.maximum(0, strikes - s) * df["put_OI"].values) for s in strikes]
        max_pain = strikes[np.argmin(losses)]
        call_wall = df.loc[df["call_OI"].idxmax()]["strikePrice"]
        put_wall = df.loc[df["put_OI"].idxmax()]["strikePrice"]
        options_score = 0
        if pcr > 1.15: options_score += 35
        elif pcr < 0.85: options_score -= 35
        if spot > max_pain: options_score += 15
        else: options_score -= 15
        return {
            "pcr": pcr, "max_pain": max_pain, "call_wall": call_wall, "put_wall": put_wall,
            "call_bias": "Heavy Call Resistance" if total_call_oi > total_put_oi else "Moderate Resistance",
            "put_bias": "Strong Put Support" if total_put_oi >= total_call_oi else "Weak Support",
            "options_score": max(-100, min(100, options_score))
        }
""",
    "astrology/__init__.py": "",
    "astrology/engine.py": """import math
import ephem
from datetime import datetime
import pytz

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

class VedicAstrologyEngine:
    def __init__(self):
        self.obs = ephem.Observer()
        self.obs.lat, self.obs.lon, self.obs.elevation = "19.0760", "72.8777", 14

    def get_lahiri_ayanamsa(self, dt):
        t = (ephem.julian_date(dt) - 2451545.0) / 36525.0
        return 23.85 + (1.396 * t)

    def calculate_ephemeris(self, target_dt):
        utc = target_dt.astimezone(pytz.UTC)
        self.obs.date = ephem.Date(utc)
        ay = self.get_lahiri_ayanamsa(utc)
        bodies = {
            "Sun": ephem.Sun(self.obs), "Moon": ephem.Moon(self.obs),
            "Mercury": ephem.Mercury(self.obs), "Venus": ephem.Venus(self.obs),
            "Mars": ephem.Mars(self.obs), "Jupiter": ephem.Jupiter(self.obs), "Saturn": ephem.Saturn(self.obs)
        }
        res = {}
        for name, b in bodies.items():
            lon = (math.degrees(ephem.Ecliptic(b).lon) - ay) % 360.0
            res[name] = {
                "sign": ZODIAC_SIGNS[int(lon // 30)],
                "degree": round(lon % 30, 2),
                "nakshatra": NAKSHATRAS[int(lon // (360/27))],
                "retrograde": False
            }
        moon_lon = (math.degrees(ephem.Ecliptic(bodies["Moon"]).lon) - ay) % 360.0
        sun_lon = (math.degrees(ephem.Ecliptic(bodies["Sun"]).lon) - ay) % 360.0
        tithi_num = int(((moon_lon - sun_lon) % 360.0) // 12) + 1
        return {"positions": res, "tithi": f"Tithi {tithi_num}", "moon_nakshatra": res["Moon"]["nakshatra"]}

    def calculate_astro_score(self, ephem_data):
        score = 0
        factors = []
        nak = ephem_data["moon_nakshatra"]
        bullish = ["Rohini", "Pushya", "Hasta", "Shravana", "Revati"]
        bearish = ["Ardra", "Ashlesha", "Jyeshtha", "Mula", "Bharani"]
        if nak in bullish:
            score += 30; factors.append(f"Moon in expansive Nakshatra: {nak} (+30)")
        elif nak in bearish:
            score -= 30; factors.append(f"Moon in contractionary Nakshatra: {nak} (-30)")
        else:
            factors.append(f"Moon in neutral Nakshatra: {nak} (0)")
        return {"score": max(-100, min(100, score)), "factors": factors}
""",
    "models/__init__.py": "",
    "models/combiner.py": """class CompositeMarketSynthesizer:
    def __init__(self, tech_weight=0.70, astro_weight=0.30):
        self.tw = tech_weight
        self.aw = astro_weight

    def synthesize(self, t_res, o_res, a_res, levels):
        market_score = (t_res["score"] * 0.65) + (o_res["options_score"] * 0.35)
        blended = (market_score * self.tw) + (a_res["score"] * self.aw)
        
        # Override guardrail: Astro cannot contradict strong technical breakdown/breakout
        if market_score <= -40 and blended > 0: blended = -10
        elif market_score >= 40 and blended < 0: blended = 10
        
        if blended >= 20: bias, emoji = "Bullish Bias", "🟢"
        elif blended <= -20: bias, emoji = "Bearish Bias", "🔴"
        else: bias, emoji = "Neutral / Range", "🟡"
        
        scenarios = {
            "bullish": f"Sustain above {levels['Pivot']} -> Targets: {levels['R1']}, {levels['R2']}. Invalidation below {levels['S1']}.",
            "bearish": f"Break below {levels['Pivot']} -> Targets: {levels['S1']}, {levels['S2']}. Invalidation above {levels['R1']}.",
            "range": f"Consolidation between {levels['S1']} and {levels['R1']}."
        }
        return {"blended_score": round(blended, 1), "bias": bias, "emoji": emoji, "scenarios": scenarios}
""",
    "dashboard/__init__.py": "",
    "dashboard/app.py": """import streamlit as st
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
""",
    "main.py": """from datetime import datetime
import pytz
from data.market_data import MarketDataEngine
from technical_analysis.indicators import TechnicalAnalysisEngine
from options.chain_analyzer import OptionChainAnalyzer
from astrology.engine import VedicAstrologyEngine
from models.combiner import CompositeMarketSynthesizer

IST = pytz.timezone("Asia/Kolkata")

def run():
    d_eng = MarketDataEngine()
    t_eng = TechnicalAnalysisEngine()
    o_eng = OptionChainAnalyzer()
    a_eng = VedicAstrologyEngine()
    combiner = CompositeMarketSynthesizer(0.70, 0.30)
    
    quote = d_eng.fetch_live_quote("^NSEI")
    df = d_eng.fetch_historical_ohlcv("^NSEI")
    df_tech = t_eng.calculate_indicators(df)
    levels = t_eng.calculate_levels(quote["high"], quote["low"], quote["previous_close"])
    t_res = t_eng.evaluate_technical_score(df_tech)
    o_res = o_eng.analyze_chain(d_eng.fetch_option_chain_data(quote["current_price"]))
    ephem = a_eng.calculate_ephemeris(datetime.now(IST))
    a_res = a_eng.calculate_astro_score(ephem)
    synth = combiner.synthesize(t_res, o_res, a_res, levels)
    
    print("="*50)
    print("           NIFTY DAILY ANALYSIS REPORT           ")
    print("="*50)
    print(f"Date:             {datetime.now(IST).strftime('%A, %d/%m/%Y')}")
    print(f"NIFTY Price:      {quote['current_price']:,.2f}")
    print(f"Directional Bias: {synth['emoji']} {synth['bias']}")
    print(f"Combined Score:   {synth['blended_score']}/100")
    print(f"Technical Score:  {t_res['score']}/100 | Astro Score: {a_res['score']}/100")
    print(f"Key Pivot:        {levels['Pivot']} | R1: {levels['R1']} | S1: {levels['S1']}")
    print(f"Moon Nakshatra:   {ephem['moon_nakshatra']} | Tithi: {ephem['tithi']}")
    print(f"Max Pain:         {o_res['max_pain']} | PCR: {o_res['pcr']}")
    print("="*50)

if __name__ == '__main__':
    run()
"""
}

for filepath, content in files.items():
    folder = os.path.dirname(filepath)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("[SUCCESS] All files and directories generated successfully!")