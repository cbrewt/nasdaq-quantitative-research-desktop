"""Offline acceptance tests for V1.2 Step 6; no Yahoo requests or file writes."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Backtesting_Engine.historical_data import calculate_historical_indicators
from Backtesting_Engine.scored_backtest import run_scored_multi_stock_backtest
from Shared_Analytics.technical_scoring import evaluate_technical_score


def fixture(length=105, *, shift=0, start="2025-03-03"):
    index = pd.bdate_range(start, periods=length)
    i = np.arange(length)
    # Deterministic advances, retreats and volume surges; valid OHLCV.
    close = (3.0 + shift + 0.019 * i + 0.33 * np.sin(i / 3.7)
             + 0.18 * np.cos(i / 7.4))
    opn = close * (1 + 0.006 * np.sin(i / 4.0))
    vol = (110000 + 4700 * (i % 9) + 5000 * np.sin(i / 3))
    frame = pd.DataFrame({
        "Open": opn, "High": np.maximum(close, opn) * 1.03,
        "Low": np.minimum(close, opn) * 0.97, "Close": close, "Volume": vol
    }, index=index)
    return frame


class Step6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = fixture()
        cls.b = fixture(shift=0.7)
        cls.dates = list(cls.a.index.date)

    def run_case(self, *, symbols=("AAA", "BBB"), loader=None, **kwargs):
        frames = {"AAA": self.a, "BBB": self.b}
        return run_scored_multi_stock_backtest(
            symbols, self.dates,
            price_loader=loader or (lambda symbol, start, end: frames[symbol]),
            min_gain_pct=0.0, min_price=1.0, max_price=10.0,
            holding_sessions=5, round_trip_cost_pct=0.50,
            **kwargs
        )

    def test_01_all_price_gain_signals_retained(self):
        result = self.run_case()
        self.assertEqual(result.analyzed_tickers, ("AAA", "BBB"))
        self.assertEqual(len(result.scored_signals), 138)  # 69 price/gain windows per fixture ticker
        self.assertEqual(result.analysis.simulation.total_signals, len(result.scored_signals))

    def test_02_scored_conditions_match_shared_logic(self):
        result = self.run_case(symbols=("AAA",))
        observations = [x for x in result.scored_signals if x.assessment.score is not None]
        self.assertTrue(observations)
        for x in observations:
            s=x.signal
            expected=evaluate_technical_score(macd=s.macd, histogram=s.histogram,
                                              rising_days=s.rising_days, rsi=s.rsi,
                                              relative_volume=s.relative_volume)
            self.assertEqual(x.assessment, expected)

    def test_03_no_future_indicator_leakage(self):
        result = self.run_case(symbols=("AAA",))
        observations = result.scored_signals
        for obs in observations[::7]:
            cutoff = obs.signal.signal_date
            prefix = calculate_historical_indicators(self.a, cutoff).iloc[-1]
            expected=evaluate_technical_score(
                macd=prefix["MACD"],histogram=prefix["Histogram"],
                rising_days=prefix["RisingDays"], rsi=prefix["RSI"],
                relative_volume=prefix["RelativeVolume"])
            self.assertEqual(obs.assessment, expected)

    def test_04_future_price_changes_do_not_change_past_scores(self):
        original = self.run_case(symbols=("AAA",))
        modified = self.a.copy()
        changed_from = self.dates[76]
        changed = modified.index.date >= changed_from
        modified.loc[changed,"Close"] *= 1.8
        modified.loc[changed,"Open"] *= 1.8
        modified.loc[changed,"High"] *= 1.8
        modified.loc[changed,"Low"] *= 1.8
        result = self.run_case(symbols=("AAA",), loader=lambda *_: modified)
        first = {o.signal.signal_date: o.assessment for o in original.scored_signals}
        later = {o.signal.signal_date: o.assessment for o in result.scored_signals}
        for day in first.keys() & later.keys():
            if day < changed_from:
                self.assertEqual(first[day], later[day])

    def test_05_all_score_groups_account_for_every_signal_and_trade(self):
        result = self.run_case()
        sim = result.analysis.simulation
        self.assertEqual(tuple(x.score for x in result.score_groups), (5,4,3,2,1,0,None))
        self.assertEqual(sum(x.signal_count for x in result.score_groups), sim.total_signals)
        self.assertEqual(sum(x.completed_trades for x in result.score_groups), len(sim.trades))
        self.assertEqual(sim.total_signals,
                         len(sim.trades) + sim.skipped_overlapping + sim.skipped_incomplete)

    def test_06_cross_score_same_symbol_overlap_is_blocked(self):
        result = self.run_case(symbols=("AAA",))
        trades = result.analysis.simulation.trades
        self.assertGreater(len(trades), 0)
        self.assertGreater(result.analysis.simulation.skipped_overlapping, 0)
        for a,b in zip(trades, trades[1:]):
            self.assertLess(a.exit_date,b.entry_date)

    def test_07_uses_existing_next_open_and_cost(self):
        result = self.run_case(symbols=("AAA",))
        trade = result.analysis.simulation.trades[0]
        signal_idx = self.dates.index(trade.signal_date)
        self.assertEqual(trade.entry_date,self.dates[signal_idx+1])
        self.assertEqual(trade.exit_date,self.dates[signal_idx+5])
        self.assertAlmostEqual(trade.entry_price,float(self.a.loc[pd.Timestamp(trade.entry_date),"Open"]))
        self.assertAlmostEqual(trade.exit_price,float(self.a.loc[pd.Timestamp(trade.exit_date),"Close"]))
        self.assertAlmostEqual(trade.net_return_pct,trade.gross_return_pct-0.5)

    def test_08_zero_trades_stats_none(self):
        result = self.run_case(symbols=("AAA",), start_date=self.dates[-1])
        self.assertEqual(result.analysis.simulation.total_signals,1)
        self.assertEqual(len(result.analysis.simulation.trades),0)
        self.assertIsNone(result.analysis.statistics)
        self.assertTrue(all(g.statistics is None for g in result.score_groups))

    def test_09_late_listed_suffix_is_supported(self):
        later=self.a.iloc[32:].copy()
        result=self.run_case(symbols=("AAA",),loader=lambda *_: later)
        self.assertEqual(result.analyzed_tickers,("AAA",))
        self.assertEqual(result.scored_signals[0].signal.signal_date,self.dates[32+20])

    def test_10_internal_missing_calendar_bar_is_reported(self):
        broken=self.b.drop(self.b.index[50])
        result=self.run_case(loader=lambda symbol,*_: self.a if symbol=="AAA" else broken)
        self.assertEqual(result.analyzed_tickers,("AAA",))
        self.assertEqual(result.excluded_tickers[0][0],"BBB")
        self.assertIn("contiguous",result.excluded_tickers[0][1])

    def test_11_download_failure_is_reported_not_counted_as_no_signals(self):
        def loader(symbol,*_):
            if symbol=="BBB":raise RuntimeError("Simulated Yahoo outage")
            return self.a
        result=self.run_case(loader=loader)
        self.assertEqual(result.analyzed_tickers,("AAA",))
        self.assertIn("Simulated Yahoo outage",result.excluded_tickers[0][1])

    def test_12_complete_provider_failure_raises(self):
        with self.assertRaisesRegex(ValueError,"No selected stocks"):
            self.run_case(loader=lambda *_: (_ for _ in ()).throw(RuntimeError("offline")))

    def test_13_missing_indicator_is_unscored_not_zero(self):
        # First 21 sessions have insufficient MACD warmup, but price/gain
        # screening is still valid; this signal is scored N/A.
        early=self.a.copy()
        # Make the initial 21-session appreciation unambiguously positive.
        early.loc[early.index[20], "Close"] = float(early.iloc[0]["Close"]) * 1.50
        early.loc[early.index[20], "High"] = max(float(early.iloc[20]["High"]),
                                                    float(early.iloc[20]["Close"]) * 1.01)
        result=self.run_case(symbols=("AAA",),end_date=self.dates[20],
                             loader=lambda *_:early)
        self.assertEqual(len(result.scored_signals),1)
        self.assertIsNone(result.scored_signals[0].assessment.score)
        self.assertEqual(result.score_groups[-1].signal_count,1)
        self.assertEqual(result.score_groups[0].signal_count,0)

    def test_14_invalid_inputs_rejected_before_download(self):
        count=[]
        loader=lambda *_:count.append(1)
        cases = [
            dict(tickers=["AAA","AAA"]),dict(tickers=["BAD!"]),
            dict(trading_dates=self.dates[::-1]),dict(min_price=-1),
            dict(min_gain_pct=float('nan')),dict(holding_sessions=0),
            dict(round_trip_cost_pct=101),dict(end_date=date(2030,1,1)),
        ]
        for c in cases:
            args=dict(tickers=["AAA"],trading_dates=self.dates,
                      price_loader=loader,min_gain_pct=0,min_price=1,max_price=10)
            args.update(c)
            with self.subTest(c=c),self.assertRaises((ValueError,TypeError)):
                run_scored_multi_stock_backtest(**args)
        self.assertFalse(count)

    def test_15_score_statistics_derived_only_from_accepted_trades(self):
        result=self.run_case()
        accepted={(t.ticker,t.signal_date):t for t in result.analysis.simulation.trades}
        lookup={(o.signal.ticker,o.signal.signal_date):o.assessment.score for o in result.scored_signals}
        for group in result.score_groups:
            returns=[t.net_return_pct for k,t in accepted.items() if lookup[k]==group.score]
            self.assertEqual(len(returns),group.completed_trades)
            if returns:
                self.assertAlmostEqual(group.statistics.expectancy_pct,sum(returns)/len(returns))
            else:self.assertIsNone(group.statistics)

    def test_16_original_engine_signature_is_unchanged(self):
        import ast
        from Backtesting_Engine.signal_engine import generate_historical_signal
        self.assertTrue(callable(generate_historical_signal))
        # Check preserved V1.1 functions without importing live provider libs.
        names = (
            ("Backtesting_Engine/multi_stock_backtest.py", "run_multi_stock_backtest"),
            ("Backtesting_Engine/screener_backtest.py", "run_screener_backtest"),
        )
        for filename, expected in names:
            source=ast.parse((ROOT/filename).read_text(encoding="utf-8"))
            self.assertIn(expected,{n.name for n in source.body if isinstance(n,ast.FunctionDef)})


if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Step6Tests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        for i in range(1,17):print(f"PASS {i}: Step 6 offline check completed.")
        print("SUCCESS: ALL 16 STEP 6 OFFLINE TESTS PASSED.")
    raise SystemExit(0 if result.wasSuccessful() else 1)
