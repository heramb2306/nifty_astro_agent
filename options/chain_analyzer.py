import pandas as pd
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
