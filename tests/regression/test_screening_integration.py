import sys,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from nasdaq_research.application.screening import ScreeningRequest,screen,display_row,number
from nasdaq_research.infrastructure.legacy_adapter import engine
class Tests(unittest.TestCase):
    def test_fixed_inputs(self):
        idx=pd.bdate_range('2025-01-01',periods=105); close=np.linspace(2,4,105); frame=pd.DataFrame({'Open':close,'Close':close,'Volume':np.arange(105)+1000},index=idx); dates=list(idx.date[-21:]); symbols=[engine.Security('AAA','Fixture')]; request=ScreeningRequest(1,10,0)
        for strict in (False,True):
            with patch.object(engine,'get_session_dates',return_value=dates),patch.object(engine,'fetch_nasdaq_symbols',return_value=symbols),patch.object(engine,'yf',object()),patch.object(engine,'extract_frame',return_value=frame),patch.object(engine,'review_reverse_splits',return_value='clear'),patch.object(engine,'yf',__import__('types').SimpleNamespace(download=lambda **kw: frame)):
                expected=engine.scan(symbols,dates,50,1.25,2,0,1,10,momentum_only=strict); actual_dates,actual,rows=screen(ScreeningRequest(1,10,0,strict)); self.assertEqual(actual_dates,dates); self.assertEqual(actual.checked,expected.checked); self.assertEqual(actual.excluded_momentum,expected.excluded_momentum); self.assertEqual(len(rows),len(expected.matches));
                for a,b in zip(rows,engine.rank_discovered_stocks(expected.matches)):
                    self.assertEqual(display_row(a),display_row(b)); pd.testing.assert_frame_equal(a.daily,b.daily)
    def test_missing_and_validation(self):
        self.assertIsNone(number(float('nan'))); self.assertEqual(number(0),0);
        with self.assertRaises(ValueError): ScreeningRequest(0,10,10)
if __name__=='__main__': unittest.main()
