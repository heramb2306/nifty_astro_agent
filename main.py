from datetime import datetime
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
