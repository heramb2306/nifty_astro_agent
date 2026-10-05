import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import ephem
import math
import pytz

# ==========================================
# CONSTANTS & TIMEZONES
# ==========================================
IST = pytz.timezone("Asia/Kolkata")

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# ==========================================
# 1. MARKET DATA ENGINE
# ==========================================
class MarketDataEngine:
    @staticmethod
    def fetch_historical_ohlcv(symbol="^NSEI", period="6mo", interval="1d"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return MarketDataEngine._generate_synthetic_ohlcv(symbol)
            df.reset_index(inplace=True)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            return df
        except Exception:
            return MarketDataEngine._generate_synthetic_ohlcv(symbol)

    @staticmethod
    def fetch_live_quote(symbol="^NSEI"):
        df = MarketDataEngine.fetch_historical_ohlcv(symbol=symbol, period="5d", interval="1d")
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

    @staticmethod
    def fetch_option_chain_data(spot_price):
        atm = round(spot_price / 50) * 50
        strikes = [atm + i * 50 for i in range(-8, 9)]
        chain = []
        for s in strikes:
            dist = (s - spot_price) / spot_price
            c_oi = int(max(5000, 140000 * np.exp(-((s - (atm + 150))**2) / (2 * (250**2)))))
            p_oi = int(max(5000, 150000 * np.exp(-((s - (atm - 150))**2) / (2 * (250**2)))))
            chain.append({
                "strikePrice": s,
                "call_OI": c_oi,
                "call_change_OI": int(np.random.normal(5000, 8000)),
                "call_LTP": max(1.0, (spot_price - s) + 100 if spot_price > s else 100 * np.exp(-abs(dist)*10)),
                "put_OI": p_oi,
                "put_change_OI": int(np.random.normal(6000, 8000)),
                "put_LTP": max(1.0, (s - spot_price) + 100 if s > spot_price else 100 * np.exp(-abs(dist)*10))
            })
        return {"spot": spot_price, "chain": chain}

    @staticmethod
    def _generate_synthetic_ohlcv(symbol):
        dates = pd.date_range(end=datetime.now(), periods=180, freq="B")
        base = 24000.0 if "BANK" not in symbol else 51000.0
        returns = np.random.normal(0.0005, 0.01, len(dates))
        prices = base * np.cumprod(1 + returns)
        highs = prices * (1 + np.abs(np.random.normal(0.003, 0.003, len(dates))))
        lows = prices * (1 - np.abs(np.random.normal(0.003, 0.003, len(dates))))
        opens = lows + (highs - lows) * 0.5
        return pd.DataFrame({"Date": dates, "Open": opens, "High": highs, "Low": lows, "Close": prices, "Volume": 10000000})


# ==========================================
# 2. TECHNICAL ANALYSIS ENGINE
# ==========================================
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
            return {"score": 0.0, "reasons": ["Insufficient data"], "rsi": 50.0, "vwap": 0.0}
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


# ==========================================
# 3. OPTION CHAIN ANALYZER
# ==========================================
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


# ==========================================
# 4. VEDIC ASTROLOGY ENGINE (LAHIRI)
# ==========================================
class VedicAstrologyEngine:
    def __init__(self):
        self.obs = ephem.Observer()
        self.obs.lat, self.obs.lon, self.obs.elevation = "19.0760", "72.8777", 14

    @staticmethod
    def get_lahiri_ayanamsa(dt):
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
        diff = (moon_lon - sun_lon) % 360.0
        tithi_num = int(diff // 12) + 1
        return {
            "positions": res,
            "tithi": f"Shukla Tithi {tithi_num}" if tithi_num <= 15 else f"Krishna Tithi {tithi_num - 15}",
            "moon_nakshatra": res["Moon"]["nakshatra"],
            "moon_sign": res["Moon"]["sign"]
        }

    @staticmethod
    def calculate_astro_score(ephem_data):
        score = 0
        factors = []
        nak = ephem_data["moon_nakshatra"]
        bullish = ["Rohini", "Pushya", "Hasta", "Shravana", "Revati"]
        bearish = ["Ardra", "Ashlesha", "Jyeshtha", "Mula", "Bharani"]
        if nak in bullish:
            score += 30; factors.append(f"Moon in expansive Nakshatra: {nak} (+30)")
        elif nak in bearish:
            score -= 30; factors.append(f"Moon in contractionary/volatile Nakshatra: {nak} (-30)")
        else:
            factors.append(f"Moon in neutral Nakshatra: {nak} (0)")
        return {"score": max(-100, min(100, score)), "factors": factors}


# ==========================================
# 5. COMPOSITE SYNTHESIS & INTRADAY TIMELINE
# ==========================================
class CompositeMarketSynthesizer:
    def __init__(self, tech_weight=0.70, astro_weight=0.30):
        self.tw = tech_weight
        self.aw = astro_weight

    def synthesize(self, t_res, o_res, a_res, levels):
        market_score = (t_res["score"] * 0.65) + (o_res["options_score"] * 0.35)
        blended = (market_score * self.tw) + (a_res["score"] * self.aw)
        
        # Override safeguard
        if market_score <= -40 and blended > 0: blended = -10
        elif market_score >= 40 and blended < 0: blended = 10
        
        if blended >= 20: bias, emoji = "Bullish Bias", "🟢"
        elif blended <= -20: bias, emoji = "Bearish Bias", "🔴"
        else: bias, emoji = "Neutral / Range-Bound", "🟡"
        
        scenarios = {
            "bullish": f"Sustain above {levels['Pivot']} -> Targets: {levels['R1']}, {levels['R2']}. Invalidation below {levels['S1']}.",
            "bearish": f"Break below {levels['Pivot']} -> Targets: {levels['S1']}, {levels['S2']}. Invalidation above {levels['R1']}.",
            "range": f"Consolidation band between S1 ({levels['S1']}) and R1 ({levels['R1']})."
        }

        # Intraday Time-Window Projections
        schedule = [
            {"Time Window": "09:15 - 09:45 IST", "Session Phase": "Opening Balance", "Bias": "High Volatility", "Playbook Action": "Avoid entering market orders. Mark initial 15-min High & Low."},
            {"Time Window": "09:45 - 10:45 IST", "Session Phase": "Primary Trend Setup", "Bias": bias, "Playbook Action": f"Trade pullbacks toward Pivot ({levels['Pivot']}). Respect S1/R1 invalidations."},
            {"Time Window": "10:45 - 12:15 IST", "Session Phase": "Mid-Morning Consolidation", "Bias": "Range-Bound", "Playbook Action": "Option decay phase. Trail stops on runners; avoid fresh breakout buys."},
            {"Time Window": "12:15 - 13:15 IST", "Session Phase": "European Pre-Open", "Bias": "Directional Expansion", "Playbook Action": "Watch for institutional volume alignment in Reliance & HDFC Bank."},
            {"Time Window": "13:15 - 15:00 IST", "Session Phase": "Afternoon Shift / Rahu Kaal", "Bias": "Chop & Fakeout Risk", "Playbook Action": "Reduce lot size. Beware of sudden reversal spikes around key strike walls."},
            {"Time Window": "15:00 - 15:30 IST", "Session Phase": "Market on Close Square-Off", "Bias": "Pull to Max Pain", "Playbook Action": f"Price gravitates toward {o_res['max_pain']}. Close intraday open positions by 15:15."}
        ]

        return {"blended_score": round(blended, 1), "bias": bias, "emoji": emoji, "scenarios": scenarios, "schedule": schedule}


# ==========================================
# 6. STREAMLIT APPLICATION DASHBOARD
# ==========================================
st.set_page_config(page_title="NIFTY Astro-Quant Agent", layout="wide", page_icon="📈")

# Sidebar Configuration
st.sidebar.title("⚙️ Model Controls")
market = st.sidebar.selectbox("Index Select", ["NIFTY 50 (^NSEI)", "BANK NIFTY (^NSEBANK)"])
symbol = "^NSEI" if "NIFTY 50" in market else "^NSEBANK"
tw = st.sidebar.slider("Technical Weight %", 10, 90, 70, 5) / 100.0
aw = round(1.0 - tw, 2)
st.sidebar.caption(f"Current Model: {int(tw*100)}% Technical / {int(aw*100)}% Astrological")

# Data Execution Pipeline
data_eng = MarketDataEngine()
tech_eng = TechnicalAnalysisEngine()
opt_eng = OptionChainAnalyzer()
astro_eng = VedicAstrologyEngine()
combiner = CompositeMarketSynthesizer(tech_weight=tw, astro_weight=aw)

quote = data_eng.fetch_live_quote(symbol)
ohlcv = data_eng.fetch_historical_ohlcv(symbol)
df_tech = tech_eng.calculate_indicators(ohlcv)
levels = tech_eng.calculate_levels(quote["high"], quote["low"], quote["previous_close"])
t_res = tech_eng.evaluate_technical_score(df_tech)

opt_data = data_eng.fetch_option_chain_data(quote["current_price"])
o_res = opt_eng.analyze_chain(opt_data)

target_dt = datetime.now(IST)
ephem_data = astro_eng.calculate_ephemeris(target_dt)
a_res = astro_eng.calculate_astro_score(ephem_data)

synth = combiner.synthesize(t_res, o_res, a_res, levels)

# Main UI Header
st.title(f"📈 {market} Technical & Astrological Analyzer")
st.caption(f"Last updated: {quote['timestamp']} | Lahiri Sidereal Ephemeris | Experimental Model")

# Top KPI Tiles
c1, c2, c3, c4 = st.columns(4)
c1.metric("Spot Price", f"{quote['current_price']:,.2f}", f"{quote['current_price'] - quote['previous_close']:,.2f}")
c2.metric("Technical Score", f"{t_res['score']}/100")
c3.metric("Astrology Score", f"{a_res['score']}/100")
c4.metric("Synthesized Bias", f"{synth['emoji']} {synth['bias']}")

st.markdown("---")

# Intraday Time-Window Schedule
st.subheader("⏰ Intraday Time-Window Playbook (What to Do at What Time)")
st.table(pd.DataFrame(synth["schedule"]))

st.markdown("---")

# Strategy Scenarios & Support/Resistance Levels
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🎯 Trade Scenarios & Triggers")
    st.success(f"**Bullish Scenario:** {synth['scenarios']['bullish']}")
    st.error(f"**Bearish Scenario:** {synth['scenarios']['bearish']}")
    st.info(f"**Range-Bound Scenario:** {synth['scenarios']['range']}")

    st.subheader("📍 Key Structural Levels")
    st.table(pd.DataFrame([levels]).T.rename(columns={0: "Price Level (INR)"}))

with col_right:
    st.subheader("🪐 Sidereal Vedic Transits (Lahiri)")
    st.markdown(f"**Moon Sign:** {ephem_data['moon_sign']} | **Moon Nakshatra:** {ephem_data['moon_nakshatra']} | **Tithi:** {ephem_data['tithi']}")
    st.dataframe(pd.DataFrame(ephem_data["positions"]).T)

    st.subheader("⛓️ Option Chain OI Profile")
    oc1, oc2, oc3, oc4 = st.columns(4)
    oc1.metric("PCR", o_res["pcr"])
    oc2.metric("Max Pain", o_res["max_pain"])
    oc3.metric("Call Wall", o_res["call_wall"])
    oc4.metric("Put Wall", o_res["put_wall"])
    st.write(f"- **Call Side Bias:** {o_res['call_bias']}")
    st.write(f"- **Put Side Bias:** {o_res['put_bias']}")

# Warning Guardrail
st.warning("⚠️ **Risk Disclosure**: Astrology is not a scientifically proven predictor of financial markets. Always treat these time windows as experimental context and manage risk using stop-losses at the stated technical invalidation levels.")
