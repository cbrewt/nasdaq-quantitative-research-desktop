import sys,unittest,gzip,hashlib,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from nasdaq_research.infrastructure.input_capture import encode_frame,decode_frame,capturing,store_capture
class Tests(unittest.TestCase):
    def test_frame(self):
        index=pd.date_range('2025-02-25',periods=4,tz='America/New_York',name='Date')
        f=pd.DataFrame({0:np.array([1.123456789012345,np.nan,-0.,np.inf]),1:np.array([1,2,3,4],dtype='int64')},index=index)
        f.columns=pd.MultiIndex.from_tuples([('ABC','Close'),('ABC','Volume')],names=['Ticker','Price'])
        pd.testing.assert_frame_equal(f,decode_frame(encode_frame(f)),check_exact=True,check_freq=False)
    def test_capture(self):
        f=pd.DataFrame({'Close':[1.,2.]},index=pd.date_range('2025-01-01',periods=2))
        yf=SimpleNamespace(download=lambda **kw:f,Ticker=lambda s:SimpleNamespace(history=lambda **kw:f))
        e=SimpleNamespace(yf=yf,requests=SimpleNamespace(get=lambda *a,**kw:SimpleNamespace(content=b'directory',status_code=200)),last_completed_calendar_date=lambda:__import__('datetime').date(2025,1,2))
        with patch('nasdaq_research.infrastructure.input_capture.metadata.version',return_value='fixture'):
            with capturing('SCAN',e) as cap:
                self.assertIs(e.yf.download(tickers=['ABC']),f); e.yf.Ticker('ABC').history(period='max'); e.requests.get('https://example.invalid'); e.last_completed_calendar_date()
            self.assertIs(e.yf,yf); self.assertEqual(len(cap.records),5); self.assertFalse(cap.errors)
        class Cursor:
            def __init__(self): self.rows=[]
            def execute(self,sql,params):
                if sql.startswith('INSERT'): self.rows.append((params[2],params[7],params[8]))
            def __iter__(self): return iter(self.rows)
        cur=Cursor(); store_capture(cur,1,cap); self.assertEqual(len(cur.rows),6)
        self.assertEqual(json.loads(gzip.decompress(cur.rows[-1][2]))['errors'],[])
    def test_empty(self):
        f=pd.DataFrame(columns=pd.MultiIndex.from_tuples([('A','Close')]))
        # Empty object columns can occur on failed downloads; capture explicitly marks unsupported types.
        f=f.astype(float); pd.testing.assert_frame_equal(f,decode_frame(encode_frame(f)),check_exact=True)
if __name__=='__main__':unittest.main()
