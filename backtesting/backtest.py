"""Backtesting engine for statistical validation of predictive edge."""
import pandas as pd
import numpy as np
from datetime import datetime

class AstrologicalTechnicalBacktester:
    def __init__(self, historical_df: pd.DataFrame, tech_engine, astro_engine):
        self.df = historical_df.copy()
        self.tech_engine = tech_engine
        self.astro_engine = astro_engine

    def run_backtest(self, window_bars: int = 150) -> dict:
        """
        Runs walk-forward simulated trades on historical bars.
        Avoids look-ahead bias by calculating ephemeris and indicators 
        strictly at the close of bar T, evaluating performance on bar T+1.
        """
        results = []
        df_indicators = self.tech_engine.calculate_indicators(self.df)
        
        for i in range(50, len(df_indicators) - 1):
            current_bar = df_indicators.iloc[:i]
            target_bar = df_indicators.iloc[i + 1]
            date_val = pd.to_datetime(current_bar.iloc[-1]["Date"])
            
            # 1. Technical signal
            tech_eval = self.tech_engine.evaluate_technical_score(current_bar)
            t_score = tech_eval["score"]
            
            # 2. Astrology signal
            ephemeris = self.astro_engine.calculate_ephemeris(date_val)
            astro_eval = self.astro_engine.calculate_astro_market_score(ephemeris)
            a_score = astro_eval["score"]
            
            # 3. Combined signal (70/30)
            combined_score = (t_score * 0.7) + (a_score * 0.3)
            
            # Forward outcome
            next_day_return = (target_bar["Close"] - current_bar.iloc[-1]["Close"]) / current_bar.iloc[-1]["Close"]
            
            results.append({
                "Date": target_bar["Date"],
                "Next_Return": next_day_return,
                "Tech_Score": t_score,
                "Astro_Score": a_score,
                "Combined_Score": combined_score,
                "Actual_Direction": 1 if next_day_return > 0 else (-1 if next_day_return < 0 else 0)
            })
            
        res_df = pd.DataFrame(results)
        
        # Calculate performance metrics
        metrics = {
            "total_samples": len(res_df),
            "tech_only": self._calculate_model_stats(res_df["Tech_Score"], res_df["Next_Return"]),
            "astro_only": self._calculate_model_stats(res_df["Astro_Score"], res_df["Next_Return"]),
            "combined": self._calculate_model_stats(res_df["Combined_Score"], res_df["Next_Return"])
        }
        return metrics

    def _calculate_model_stats(self, score_series: pd.Series, return_series: pd.Series) -> dict:
        signals = np.where(score_series > 15, 1, np.where(score_series < -15, -1, 0))
        strategy_returns = signals * return_series
        
        # Non-zero trade filtered
        trade_indices = np.where(signals != 0)[0]
        if len(trade_indices) == 0:
            return {"win_rate": 0.0, "sharpe": 0.0, "total_signals": 0}
            
        winning_trades = np.sum(strategy_returns[trade_indices] > 0)
        win_rate = winning_trades / len(trade_indices)
        
        mean_ret = np.mean(strategy_returns[trade_indices])
        std_ret = np.std(strategy_returns[trade_indices]) + 1e-9
        sharpe = (mean_ret / std_ret) * np.sqrt(252)
        
        # Max drawdown
        cum_ret = np.cumprod(1 + strategy_returns[trade_indices])
        peak = np.maximum.accumulate(cum_ret)
        drawdown = (cum_ret - peak) / peak
        max_dd = np.min(drawdown) if len(drawdown) > 0 else 0.0
        
        return {
            "win_rate": round(float(win_rate) * 100, 2),
            "sharpe_ratio": round(float(sharpe), 2),
            "max_drawdown_pct": round(float(max_dd) * 100, 2),
            "total_signals": int(len(trade_indices))
        }