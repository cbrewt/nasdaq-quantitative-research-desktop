import sys, unittest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from nasdaq_research.infrastructure.legacy_adapter import engine
from nasdaq_research.application import strict_capture as c
from Backtesting_Engine import multi_stock_backtest as original

class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.dates=[date(2025,2,20)+timedelta(days=i) for i in range(75)]
        self.suffix=self.dates[6:]
    def test_verified(self):
        self.assertEqual(c.eligible_calendar('STAK',self.dates,self.suffix),self.suffix)
    def test_full_unknown(self):
        self.assertEqual(c.eligible_calendar('ABC',self.dates,self.dates),self.dates)
    def test_reject(self):
        for symbol,obs in [('ABC',self.suffix),('STAK',self.suffix[1:]),('STAK',self.suffix[:-1]),('STAK',self.suffix[:3]+self.suffix[4:]),('STAK',self.suffix+[self.suffix[-1]]),('STAK',self.suffix[::-1]),('STAK',self.dates),('STAK',self.suffix+[date(2026,1,1)]),('STAK',[])]:
            with self.subTest(symbol=symbol,obs=len(obs)):
                with self.assertRaises(ValueError): c.eligible_calendar(symbol,self.dates,obs)
    def test_actual_engine_parity(self):
        values=[2*(1.022**i)+.12*((i%7)/7) for i in range(len(self.suffix))]
        frame=pd.DataFrame({'Open':values,'High':[v+.1 for v in values],'Low':[v-.1 for v in values],'Close':values,'Volume':[1000+i*30 for i in range(len(values))]},index=pd.to_datetime(self.suffix))
        with patch.object(original,'download_historical_prices',return_value=frame):
            a=original.run_multi_stock_backtest(['STAK'],self.suffix)
        with patch.object(c,'download_historical_prices',return_value=frame):
            b=c.run_multi_stock_backtest(['STAK'],self.dates)
        self.assertEqual(a.analysis,b.analysis); self.assertEqual(a.signal_counts,b.signal_counts)
        self.assertTrue(all(x.signal_date>=self.suffix[20] for x in b.signals))
    def test_insufficient_history(self):
        dates=self.dates[:15]; suffix=dates[6:]
        # global calendar must have 21 sessions; use a later verified listing fixture
        dates=self.dates[:25]; suffix=dates[-5:]
        frame=pd.DataFrame(index=pd.to_datetime(suffix))
        with patch.dict(c.VERIFIED_LISTINGS,{'ABC':(suffix[0],'fixture')}),patch.object(c,'download_historical_prices',return_value=frame),patch.object(c,'evaluate_historical_period') as evaluate:
            result=c.run_multi_stock_backtest(['ABC'],dates)
        evaluate.assert_not_called(); self.assertEqual(result.signals,())
    def test_registry_lse(self):
        dates=[date(2024,12,18),date(2024,12,19),date(2024,12,20)]
        self.assertEqual(c.eligible_calendar('LSE',dates,dates[1:]),dates[1:])
        with self.assertRaises(ValueError): c.eligible_calendar('LSE',dates,dates[2:])
    def test_preflight_aggregates(self):
        frame=pd.DataFrame(index=pd.to_datetime(self.dates[1:]))
        with patch.object(c,'download_historical_prices',return_value=frame) as download, patch.object(c,'evaluate_historical_period') as evaluate:
            with self.assertRaisesRegex(ValueError, r'ABC:.*XYZ:'):
                c.run_multi_stock_backtest(['ABC','XYZ'],self.dates)
        self.assertEqual(download.call_count,2)
        evaluate.assert_not_called()
if __name__=='__main__': unittest.main()
