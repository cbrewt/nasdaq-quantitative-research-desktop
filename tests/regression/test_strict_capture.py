import sys, unittest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from nasdaq_research.infrastructure.legacy_adapter import engine
from nasdaq_research.application import strict_capture as capture
from Backtesting_Engine import multi_stock_backtest as original
from Backtesting_Engine.signal_engine import HistoricalSignal
class Parity(unittest.TestCase):
    def test_strict_capture(self):
        dates=[date(2025,1,1)+timedelta(days=i) for i in range(35)]
        frame=pd.DataFrame({'Open':[4.0]*35,'High':[5.0]*35,'Low':[3.0]*35,'Close':[4.5]*35,'Volume':[1000]*35},index=pd.to_datetime(dates))
        signals=[HistoricalSignal('ABC',dates[i],3.0,4.5,50.0,.2,.1,3,60.,2.) for i in (20,21,27,34)]
        with patch.object(original,'download_historical_prices',return_value=frame),patch.object(original,'evaluate_historical_period',return_value=signals):
            a=original.run_multi_stock_backtest(['ABC'],dates)
        with patch.object(capture,'download_historical_prices',return_value=frame),patch.object(capture,'evaluate_historical_period',return_value=signals):
            b=capture.run_multi_stock_backtest(['ABC'],dates)
        self.assertEqual(a.analysis,b.analysis); self.assertEqual(a.signal_counts,b.signal_counts); self.assertEqual(b.signals,tuple(signals)); self.assertEqual(b.analysis.simulation.total_signals,4)
        self.assertGreater(b.analysis.simulation.skipped_overlapping,0); self.assertGreater(b.analysis.simulation.skipped_incomplete,0)
if __name__=='__main__': unittest.main()
