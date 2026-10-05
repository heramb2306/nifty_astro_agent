import pandas as pd
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
