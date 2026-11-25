import sys, unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from nasdaq_research.application.screening import ScreeningRequest,screen_background,ScreeningCancelled,engine
class Tests(unittest.TestCase):
    def test_batches(self):
        symbols=list(range(105)); token=Event(); progress=[]; sizes=[]
        class FastToken(Event):
            def wait(self,timeout=None): return self.is_set()
        def scan(group,*args,**kw):
            sizes.append(len(group)); return engine.ScanResult([],len(group),len(group),0,0,0,0)
        with patch.object(engine,'get_session_dates',return_value=[1]),patch.object(engine,'fetch_nasdaq_symbols',return_value=symbols),patch.object(engine,'scan',side_effect=scan):
            dates,result,rows=screen_background(ScreeningRequest(1,10,10),FastToken(),lambda *x:progress.append(x))
        self.assertEqual(sizes,[50,50,5]); self.assertEqual(result.checked,105); self.assertEqual(result.missing,105); self.assertEqual(progress[-1][:2],(105,105)); self.assertEqual(rows,[])
    def test_cancel(self):
        token=Event(); token.set()
        with patch.object(engine,'get_session_dates') as dates:
            with self.assertRaises(ScreeningCancelled): screen_background(ScreeningRequest(1,10,10),token,lambda *x:None)
            dates.assert_not_called()
    def test_cancel_after_batch(self):
        token=Event()
        def scan(group,*args,**kw):
            token.set(); return engine.ScanResult([],0,len(group),0,0,0,0)
        with patch.object(engine,'get_session_dates',return_value=[1]),patch.object(engine,'fetch_nasdaq_symbols',return_value=list(range(105))),patch.object(engine,'scan',side_effect=scan) as call:
            with self.assertRaises(ScreeningCancelled): screen_background(ScreeningRequest(1,10,10),token,lambda *x:None)
            self.assertEqual(call.call_count,1)
if __name__=='__main__': unittest.main()
