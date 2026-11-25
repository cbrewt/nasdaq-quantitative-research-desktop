import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import pandas as pd
from nasdaq_research.presentation.charts import extract,Chart,PANELS
from PySide6.QtWidgets import QApplication
class TestCharts(unittest.TestCase):
    def test_observations(self):
        frame=pd.DataFrame({'Close':[1.23456789,float('nan'),3.0],'Volume':[10,20,30],'Histogram':[-.1,0,.1]},index=pd.date_range('2026-01-01',periods=3))
        dates,values=extract(frame)
        self.assertEqual(dates,['2026-01-01','2026-01-02','2026-01-03'])
        self.assertEqual(values['Close'],[1.23456789,None,3.0]); self.assertEqual(values['Signal'],[None]*3); self.assertEqual(values['Histogram'],[-.1,0,.1])
        app=QApplication.instance() or QApplication([])
        for panel in PANELS:
            widget=Chart(panel); widget.resize(640,155); widget.set_data(dates,values); self.assertFalse(widget.grab().isNull())
if __name__=='__main__': unittest.main()
