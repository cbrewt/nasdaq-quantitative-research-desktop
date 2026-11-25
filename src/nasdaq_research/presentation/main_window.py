"""UID-001 screening integration; background screening and cooperative cancellation."""
from ..application.screening import ScreeningRequest, screen, screen_background, ScreeningCancelled, display_row, number
from threading import Event
from PySide6.QtCore import Qt, QSortFilterProxyModel, QRegularExpression, QObject, QThread, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QListWidget,QStackedWidget,QDoubleSpinBox,QComboBox,QLineEdit,QTableView,QHeaderView,QMessageBox,QGroupBox,QApplication,QProgressBar)

NAMES = ['Stock Screener','Stock Analysis','Backtesting','Research History','Reports','Settings']
# Fictional measurements, not calculated by the Version 1.2 engine.
ROWS = [('DEMO-A',4.82,18.4,0.182,0.046,3,63.4,1.84,1200000),('DEMO-B',7.25,15.2,0.11,0.02,2,58.1,1.56,950000),('DEMO-C',2.64,12.7,-0.03,0.01,3,72.1,1.21,640000),('DEMO-D',5.12,11.3,0.04,-0.01,0,54.2,0.92,420000)]
def conditions(r):
    return (r[3]>0,r[4]>0,r[5]>=3,50<=r[6]<=70,r[7]>1)
def display_text(column, value):
    """Format display text only; preserve raw numbers in the model's sort role."""
    if column == 0:
        return str(value)
    n = number(value)
    if n is None:
        return 'N/A'
    if column in (3, 6):
        return str(int(n))
    if column == 9:
        return f'{n:,.2f}'
    places = 6 if column in (4, 5) else 2
    text = format(n, f'.{places}f')
    if n != 0 and float(text) == 0:
        return format(n, '.3e')
    return text

class ScanWorker(QObject):
    progress = Signal(int, int, str)
    succeeded = Signal(object, object, object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, request, token):
        super().__init__()
        self.request, self.token = request, token

    @Slot()
    def run(self):
        try:
            result = screen_background(self.request, self.token, self.progress.emit)
            if self.token.is_set():
                self.cancelled.emit()
            else:
                self.succeeded.emit(*result)
        except ScreeningCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Nasdaq Quantitative Research V2.0 — Prototype'); self.resize(1280,800); self.setMinimumSize(800,560)
        self.setStyleSheet('''QWidget {background:#141e2c;color:#e5edf6;font-size:14px;} QGroupBox {border:1px solid #394b62;border-radius:6px;margin-top:14px;padding:12px;} QGroupBox::title {subcontrol-origin:margin;left:12px;} QListWidget,QTableView,QLineEdit,QDoubleSpinBox,QComboBox {background:#202e40;border:1px solid #45566b;padding:5px;} QListWidget::item {padding:13px;} QListWidget::item:selected {background:#315c83;} QPushButton {background:#25689e;padding:9px 15px;border-radius:5px;} QPushButton:disabled {background:#303b49;color:#a6b3c2;} QHeaderView::section {background:#2b3d53;padding:7px;border:0;} QTableView {alternate-background-color:#192637;gridline-color:#36465a;} QLabel#heading {font-size:25px;font-weight:bold;} QWidget:focus {outline:1px solid #8ac8fb;}''')
        root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root)
        banner=QLabel('LIVE SCREENING • Sample preview available • Database not connected'); banner.setStyleSheet('background:#4b3821;color:#ffe3b0;padding:10px;font-weight:bold'); outer.addWidget(banner)
        body=QHBoxLayout(); outer.addLayout(body,1); self.nav=QListWidget(); self.nav.addItems(NAMES); self.nav.setFixedWidth(215); body.addWidget(self.nav); self.stack=QStackedWidget(); body.addWidget(self.stack,1)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self._thread=None; self._worker=None; self._token=None; self.live_matches=None; self.make_screener(); self.make_analysis()
        for name,description in [('Backtesting','Historical simulation, signals, trades and statistics — integration in Milestone 09.'),('Research History','Saved research runs and parameters — database integration in Milestone 10.'),('Reports','Word report generation and retrieval — integration in Milestone 09.'),('Settings','Application and database configuration — not connected. No credentials are requested or stored.')]:
            _,layout=self.page(name); label=QLabel(description); label.setWordWrap(True); layout.addWidget(label); layout.addStretch()
        for name in ['File','Research','View','Tools','Help']:
            menu=self.menuBar().addMenu(name)
            if name=='File': menu.addAction('Exit',self.close)
            elif name=='Help': menu.addAction('About prototype',lambda: QMessageBox.information(self,'Prototype','UID-001 screening integration. Background processing and cooperative cancellation enabled.'))
            else:
                for i,title in enumerate(NAMES): menu.addAction(title,lambda checked=False,i=i:self.nav.setCurrentRow(i))
        self.nav.setCurrentRow(0); self.statusBar().showMessage('Ready | Database: not connected')
    def page(self,name):
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(20,14,20,14); label=QLabel(name); label.setObjectName('heading'); layout.addWidget(label); self.stack.addWidget(page); return page,layout
    def make_screener(self):
        _,layout=self.page(NAMES[0]); group=QGroupBox('Screening parameters'); form=QFormLayout(group); self.minimum=QDoubleSpinBox(); self.maximum=QDoubleSpinBox(); self.gain=QDoubleSpinBox()
        for control,value in [(self.minimum,1),(self.maximum,10),(self.gain,10)]: control.setRange(0,1000000); control.setDecimals(2); control.setValue(value)
        self.minimum.setPrefix('$'); self.maximum.setPrefix('$'); self.gain.setSuffix('%'); form.addRow('Minimum price',self.minimum); form.addRow('Maximum price',self.maximum); form.addRow('Minimum gain',self.gain); form.addRow('Observation window',QLabel('21 completed trading sessions')); form.addRow('Reverse splits',QLabel('Excluded (mandatory)')); self.mode=QComboBox(); self.mode.addItems(['Research Mode','Strict Mode']); form.addRow('Mode',self.mode); layout.addWidget(group)
        controls=QHBoxLayout(); self.run=QPushButton('Preview sample results'); self.run.clicked.connect(self.preview); controls.addWidget(self.run); self.live=QPushButton('Run live screener'); self.live.clicked.connect(self.run_live); controls.addWidget(self.live); self.cancel=QPushButton('Cancel'); self.cancel.setEnabled(False); self.cancel.clicked.connect(self.cancel_scan); controls.addWidget(self.cancel); layout.addLayout(controls); self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0); layout.addWidget(self.progress)
        self.summary=QLabel('No preview loaded'); self.summary.setWordWrap(True); layout.addWidget(self.summary); self.filter=QLineEdit(); self.filter.setPlaceholderText('Filter ticker'); layout.addWidget(self.filter)
        self.model=QStandardItemModel(0,10,self); self.model.setHorizontalHeaderLabels(['Ticker','Close ($)','Gain (%)','Score / 5','MACD','Histogram','Rising days','RSI','RVOL','Median dollar volume']); self.proxy=QSortFilterProxyModel(self); self.proxy.setSourceModel(self.model); self.proxy.setSortRole(Qt.ItemDataRole.UserRole); self.proxy.setFilterKeyColumn(0); self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive); self.filter.textChanged.connect(self.proxy.setFilterFixedString)
        self.table=QTableView(); self.table.setModel(self.proxy); self.table.setSortingEnabled(True); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows); self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents); self.table.doubleClicked.connect(self.open_analysis); layout.addWidget(self.table,1); btn=QPushButton('Analyze selected stock'); btn.clicked.connect(lambda:self.open_analysis(self.table.currentIndex())); layout.addWidget(btn)
    def preview(self):
        self.live_matches=None; self.detail.setText('Select a sample from Stock Screener.')
        if self.minimum.value()>self.maximum.value(): self.summary.setText('Invalid price range: minimum exceeds maximum.'); self.model.removeRows(0,self.model.rowCount()); return
        self.model.removeRows(0,self.model.rowCount())
        for r in ROWS:
            if not self.minimum.value()<=r[1]<=self.maximum.value() or r[2]<self.gain.value(): continue
            # Strict-mode preview is deliberately disabled: actual strict rules require engine integration.
            if self.mode.currentIndex()==1: continue
            vals=(r[0],r[1],r[2],sum(conditions(r)),*r[3:]); items=[]
            for i,v in enumerate(vals):
                item=QStandardItem(display_text(i,v)); item.setData(v,Qt.ItemDataRole.UserRole); items.append(item)
            self.model.appendRow(items)
        self.summary.setText('Strict Mode preview unavailable until engine integration.' if self.mode.currentIndex()==1 else f'{self.model.rowCount()} fictional sample matches — not a real scan.'); self.table.sortByColumn(3,Qt.SortOrder.DescendingOrder)
    def make_analysis(self):
        _,layout=self.page(NAMES[1]); self.detail=QLabel('Select a stock from Stock Screener.'); self.detail.setWordWrap(True); self.detail.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.detail); layout.addWidget(QLabel('Price and indicator charts: scheduled for Milestone 08.')); layout.addStretch()
    def open_analysis(self,index):
        if not index.isValid(): return
        ticker=self.proxy.index(index.row(),0).data()
        if self.live_matches is not None:
            m=self.live_matches[ticker]; score=m.technical_score; vals=display_row(m)
            labels=['MACD > 0','Histogram > 0','At least 3 consecutive histogram increases','RSI 50–70 inclusive','RVOL > 1']
            lines=[]
            for label,value,flag in zip(labels,vals[4:9],score.conditions.values()):
                n=number(value); lines.append(f'{label}: {"N/A" if n is None else format(n,".6g")} — {"N/A" if flag is None else int(flag)} point')
            self.detail.setText(f'{ticker} — live scan, session {self.session_date}\nClose ${m.last_close:.2f} | Gain {m.gain_pct:.4f}% | Score {score.label}\n\n'+'\n'.join(lines)); self.nav.setCurrentRow(1); return
        r=next(x for x in ROWS if x[0]==ticker); labels=['MACD > 0','Histogram > 0','At least 3 consecutive histogram increases','RSI 50–70 inclusive','RVOL > 1']; self.detail.setText(f'{ticker} — fictional sample\nClose ${r[1]:.2f} | Gain {r[2]}% | Score {sum(conditions(r))}/5\n\n'+'\n'.join(f'{label}: {value} — {int(ok)} point' for label,value,ok in zip(labels,r[3:8],conditions(r)))+f'\n\nMedian daily dollar volume: ${r[8]:,}'); self.nav.setCurrentRow(1)

    def run_live(self):
        if self._thread is not None: return
        try: request=ScreeningRequest(self.minimum.value(),self.maximum.value(),self.gain.value(),self.mode.currentIndex()==1)
        except ValueError as exc: self.summary.setText(str(exc)); return
        if QMessageBox.question(self,'Live screening','Scan the full Nasdaq directory in the background? Cancellation takes effect at a safe batch boundary.') != QMessageBox.StandardButton.Yes: return
        self.start_scan(request)

    def start_scan(self, request):
        if self._thread is not None: return
        self.live_matches={}; self.model.removeRows(0,self.model.rowCount()); self.detail.setText('No current result'); self.filter.clear()
        self.summary.setText('Starting live scan'); self.statusBar().showMessage('Scanning in background'); self.progress.setRange(0,0)
        for control in (self.live,self.run,self.minimum,self.maximum,self.gain,self.mode): control.setEnabled(False)
        self.cancel.setEnabled(True)
        self._token=Event(); self._thread=QThread(self); self._worker=ScanWorker(request,self._token); self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.update_progress)
        self._worker.succeeded.connect(self.scan_succeeded)
        self._worker.failed.connect(self.scan_failed)
        self._worker.cancelled.connect(self.scan_cancelled)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self.scan_finished)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @Slot(int,int,str)
    def update_progress(self, checked,total,message):
        if self._token is not None and self._token.is_set(): return
        self.progress.setRange(0,total if total else 0); self.progress.setValue(checked); self.summary.setText(message)

    @Slot()
    def cancel_scan(self):
        if self._token is None: return
        self._token.set(); self.cancel.setEnabled(False); self.summary.setText('Cancellation requested — finishing current operation'); self.statusBar().showMessage('Cancelling')

    @Slot(object,object,object)
    def scan_succeeded(self,dates,result,matches):
        if self._token is not None and self._token.is_set(): self.scan_cancelled(); return
        self.show_live(dates,result,matches); self.progress.setRange(0,100); self.progress.setValue(100); self.cancel.setEnabled(False)

    @Slot(str)
    def scan_failed(self,message):
        self.progress.setRange(0,100); self.progress.setValue(0); self.summary.setText('Scan failed: '+message); self.statusBar().showMessage('Scan failed'); self.cancel.setEnabled(False)

    @Slot()
    def scan_cancelled(self):
        self.progress.setRange(0,100); self.progress.setValue(0); self.summary.setText('Scan cancelled — no partial results retained'); self.statusBar().showMessage('Scan cancelled'); self.cancel.setEnabled(False)

    @Slot()
    def scan_finished(self):
        self._thread=None; self._worker=None; self._token=None
        for control in (self.live,self.run,self.minimum,self.maximum,self.gain,self.mode): control.setEnabled(True)
        self.cancel.setEnabled(False)

    def closeEvent(self,event):
        if self._thread is not None:
            self.cancel_scan(); event.ignore(); self.statusBar().showMessage('Cancellation requested; close again after scan stops')
        else: super().closeEvent(event)

    def show_live(self,dates,result,matches):
        self.session_date=dates[-1]; self.live_matches={m.security.ticker:m for m in matches}; self.model.removeRows(0,self.model.rowCount()); self.table.setSortingEnabled(False)
        for m in matches:
            items=[]
            for i,v in enumerate(display_row(m)):
                n=number(v) if i else None
                text=display_text(i,v)
                item=QStandardItem(text); item.setData(v if i==0 else (n if n is not None else float('-inf')),Qt.ItemDataRole.UserRole); items.append(item)
            self.model.appendRow(items)
        self.proxy.sort(-1); self.table.horizontalHeader().setSortIndicator(-1,Qt.SortOrder.AscendingOrder); self.table.setSortingEnabled(True)
        self.summary.setText(f'Completed sessions {dates[0]} to {dates[-1]} | Checked {result.checked} | Qualified {len(matches)} | Incomplete prices {result.missing} | Reverse splits {result.excluded_reverse} | Unverified splits {result.excluded_unverified} | Momentum exclusions {result.excluded_momentum}')
        self.statusBar().showMessage('Scan complete | Database not connected')
