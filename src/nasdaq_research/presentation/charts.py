"""Read-only charts of the exact completed scan observations; no recalculation."""
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPointF, QRectF
from ..application.screening import number

PANELS = (("Closing price ($)", (("Close", "#8ac8fb"),), None),
          ("Trading volume (shares)", (("Volume", "#8ac8fb"),), 0),
          ("MACD and signal", (("MACD", "#8ac8fb"), ("Signal", "#f0bd72")), 0),
          ("MACD histogram", (("Histogram", "#72d5a5"),), 0),
          ("RSI", (("RSI", "#c3a5fb"),), (30,50,70)),
          ("Relative volume", (("RelativeVolume", "#8ac8fb"),), 1))

def extract(frame):
    dates = [str(x)[:10] for x in frame.index]
    values = {key: [number(x) for x in frame[key]] if key in frame else [None]*len(dates)
              for _, series, _ in PANELS for key, _ in series}
    return dates, values

class Chart(QWidget):
    def __init__(self, panel):
        super().__init__(); self.panel=panel; self.dates=[]; self.values={}
        self.setMinimumHeight(155); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
    def set_data(self, dates, values):
        self.dates=dates; self.values=values; self.update()
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor('#1b293a')); title,series,ref=self.panel
        painter.setPen(QColor('#e5edf6')); painter.drawText(10,19,title)
        points=[v for key,_ in series for v in self.values.get(key,[]) if v is not None]
        if not points:
            painter.drawText(10,52,'No recorded observations'); return
        refs=[] if ref is None else list(ref) if isinstance(ref,tuple) else [ref]
        lo=min(points+refs); hi=max(points+refs)
        if lo==hi: lo-=max(abs(lo)*.05, .01); hi+=max(abs(hi)*.05,.01)
        left,right,top,bottom=83,max(84,self.width()-14),32,self.height()-24
        def y(v): return bottom-(v-lo)/(hi-lo)*(bottom-top)
        def x(i): return left+(right-left)*i/max(1,len(self.dates)-1)
        for value in (lo,(lo+hi)/2,hi):
            painter.setPen(QColor('#42536a')); painter.drawLine(QPointF(left,y(value)),QPointF(right,y(value)))
            painter.setPen(QColor('#c8d3df')); painter.drawText(QRectF(2,y(value)-8,left-8,16),Qt.AlignmentFlag.AlignRight,format(value,'.4g'))
        for value in refs:
            pen=QPen(QColor('#a3afbd')); pen.setStyle(Qt.PenStyle.DashLine); painter.setPen(pen); painter.drawLine(QPointF(left,y(value)),QPointF(right,y(value)))
        for j,(key,color) in enumerate(series):
            vals=self.values.get(key,[]); painter.setPen(QColor(color)); painter.drawText(max(left,right-155*(len(series)-j)),19,key)
            previous=None
            for i,v in enumerate(vals):
                if v is None: previous=None; continue
                point=QPointF(x(i),y(v))
                if key in ('Volume','Histogram'):
                    c=QColor('#e47d82' if v<0 else color); painter.setPen(c); width=max(1,(right-left)/max(1,len(vals))*.65)
                    painter.fillRect(QRectF(x(i)-width/2,min(y(0),y(v)),width,max(1,abs(y(0)-y(v)))),c)
                else:
                    painter.setPen(QPen(QColor(color),2)); painter.drawPoint(point)
                    if previous is not None: painter.drawLine(previous,point)
                previous=point
        painter.setPen(QColor('#c8d3df')); painter.drawText(left,self.height()-5,self.dates[0]); painter.drawText(QRectF(left,self.height()-20,right-left,20),Qt.AlignmentFlag.AlignRight,self.dates[-1])
