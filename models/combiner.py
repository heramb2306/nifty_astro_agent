class CompositeMarketSynthesizer:
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
