"""UID-001 screening integration; background screening and cooperative cancellation."""
from ..application.screening import ScreeningRequest, screen, screen_background, ScreeningCancelled, display_row, number
from threading import Event
from PySide6.QtCore import Qt, QSortFilterProxyModel, QRegularExpression, QObject, QThread, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QListWidget,QStackedWidget,QDoubleSpinBox,QComboBox,QLineEdit,QTableView,QHeaderView,QMessageBox,QGroupBox,QApplication,QProgressBar,QScrollArea)
from .charts import Chart, PANELS, extract
from ..application.historical import export_scan, historical
from pathlib import Path
from uuid import uuid4
from ..infrastructure.repository import Repository, utc
from ..infrastructure.input_capture import capturing, json_bytes
from ..infrastructure.legacy_adapter import engine
from dataclasses import asdict
from PySide6.QtWidgets import QInputDialog, QTableWidget, QTableWidgetItem
from PySide6.QtWidgets import QFileDialog, QSpinBox
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

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
    succeeded = Signal(object, object, object, object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, request, token):
        super().__init__()
        self.request, self.token = request, token

    @Slot()
    def run(self):
        try:
            with capturing("SCAN",engine) as capture:
                capture.add("SCREEN_PARAMETERS","local",{},json_bytes(asdict(self.request)),"json")
                result = screen_background(self.request, self.token, self.progress.emit)
            if self.token.is_set():
                self.cancelled.emit()
            else:
                self.succeeded.emit(*result,capture)
        except ScreeningCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

class HistoricalWorker(QObject):
    succeeded=Signal(object,object,object,object)
    failed=Signal(str)
    finished=Signal()
    def __init__(self,snapshot,directory,years,holding,cost):
        super().__init__(); self.args=(snapshot,directory,years,holding,cost)
    @Slot()
    def run(self):
        try:
            h,report=export_scan(*self.args)
            from Backtesting_Engine import market_data_provider
            from ..application.strict_capture import VERIFIED_LISTINGS
            with capturing("BACKTEST",engine,market_data_provider,VERIFIED_LISTINGS) as capture:
                capture.add("HISTORICAL_HANDOFF","local",{},(report.parent/"handoff.json").read_bytes(),"raw-bytes")
                result,path=historical(h,report)
            self.succeeded.emit(result,path,report,capture)
        except Exception as exc: self.failed.emit(str(exc))
        finally: self.finished.emit()

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Nasdaq Quantitative Research V2.0 — Prototype'); self.resize(1280,800); self.setMinimumSize(800,560)
        self.setStyleSheet('''QWidget {background:#141e2c;color:#e5edf6;font-size:14px;} QGroupBox {border:1px solid #394b62;border-radius:6px;margin-top:14px;padding:12px;} QGroupBox::title {subcontrol-origin:margin;left:12px;} QListWidget,QTableView,QLineEdit,QDoubleSpinBox,QComboBox {background:#202e40;border:1px solid #45566b;padding:5px;} QListWidget::item {padding:13px;} QListWidget::item:selected {background:#315c83;} QPushButton {background:#25689e;padding:9px 15px;border-radius:5px;} QPushButton:disabled {background:#303b49;color:#a6b3c2;} QHeaderView::section {background:#2b3d53;padding:7px;border:0;} QTableView {alternate-background-color:#192637;gridline-color:#36465a;} QLabel#heading {font-size:25px;font-weight:bold;} QWidget:focus {outline:1px solid #8ac8fb;}''')
        root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root)
        self._report_thread=None; self._report_worker=None; self.repo=None; self._db_thread=None; self._db_worker=None; self.saved_uuid=None; self.banner=QLabel('LIVE SCREENING • Sample preview available • Database not connected'); banner=self.banner; banner.setStyleSheet('background:#4b3821;color:#ffe3b0;padding:10px;font-weight:bold'); outer.addWidget(banner)
        body=QHBoxLayout(); outer.addLayout(body,1); self.nav=QListWidget(); self.nav.addItems(NAMES); self.nav.setFixedWidth(215); body.addWidget(self.nav); self.stack=QStackedWidget(); body.addWidget(self.stack,1)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self._thread=None; self._worker=None; self._token=None; self.live_matches=None; self.snapshot=None; self._history_thread=None; self.make_screener(); self.make_analysis(); self.make_backtesting()
        self.make_research_history(); self.make_reports(); self.make_database_settings()
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
        self.snapshot=None; self.clear_charts(); self.live_matches=None; self.detail.setText('Select a sample from Stock Screener.')
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
        _,layout=self.page(NAMES[1]); scroll=QScrollArea(); scroll.setWidgetResizable(True); content=QWidget(); inner=QVBoxLayout(content); scroll.setWidget(content); layout.addWidget(scroll,1)
        self.detail=QLabel('Select a stock from Stock Screener.'); self.detail.setWordWrap(True); self.detail.setTextFormat(Qt.TextFormat.PlainText); inner.addWidget(self.detail)
        self.chart_note=QLabel('Charts require a completed live scan.'); self.chart_note.setWordWrap(True); inner.addWidget(self.chart_note)
        self.charts=[Chart(panel) for panel in PANELS]
        for chart in self.charts: inner.addWidget(chart); chart.hide()
        inner.addStretch()
    def clear_charts(self):
        self.chart_note.setText('Charts require a completed live scan; sample rows have no historical series.')
        for chart in self.charts: chart.set_data([],{}); chart.hide()
    def show_charts(self,match):
        dates,values=extract(match.daily); self.chart_note.setText('Recorded completed-session observations from this scan. Missing values are gaps; no additional data requested.')
        for chart in self.charts: chart.set_data(dates,values); chart.show()
    def open_analysis(self,index):
        if not index.isValid(): return
        ticker=self.proxy.index(index.row(),0).data()
        if self.live_matches is not None:
            m=self.live_matches[ticker]; score=m.technical_score; vals=display_row(m)
            labels=['MACD > 0','Histogram > 0','At least 3 consecutive histogram increases','RSI 50–70 inclusive','RVOL > 1']
            lines=[]
            for label,value,flag in zip(labels,vals[4:9],score.conditions.values()):
                n=number(value); lines.append(f'{label}: {"N/A" if n is None else format(n,".6g")} — {"N/A" if flag is None else int(flag)} point')
            self.detail.setText(f'{ticker} — live scan, session {self.session_date}\nClose ${m.last_close:.2f} | Gain {m.gain_pct:.4f}% | Score {score.label}\n\n'+'\n'.join(lines)); self.show_charts(m); self.nav.setCurrentRow(1); return
        self.clear_charts(); r=next(x for x in ROWS if x[0]==ticker); labels=['MACD > 0','Histogram > 0','At least 3 consecutive histogram increases','RSI 50–70 inclusive','RVOL > 1']; self.detail.setText(f'{ticker} — fictional sample\nClose ${r[1]:.2f} | Gain {r[2]}% | Score {sum(conditions(r))}/5\n\n'+'\n'.join(f'{label}: {value} — {int(ok)} point' for label,value,ok in zip(labels,r[3:8],conditions(r)))+f'\n\nMedian daily dollar volume: ${r[8]:,}'); self.nav.setCurrentRow(1)

    def run_live(self):
        if self._thread is not None: return
        try: request=ScreeningRequest(self.minimum.value(),self.maximum.value(),self.gain.value(),self.mode.currentIndex()==1)
        except ValueError as exc: self.summary.setText(str(exc)); return
        if QMessageBox.question(self,'Live screening','Scan the full Nasdaq directory in the background? Cancellation takes effect at a safe batch boundary.') != QMessageBox.StandardButton.Yes: return
        self.start_scan(request)

    def start_scan(self, request):
        if self._thread is not None or self._history_thread is not None or self._report_thread is not None: return
        self.snapshot=None; self.scan_request=request; self.scan_started=utc(); self.saved_uuid=None
        self.clear_charts(); self.live_matches={}; self.model.removeRows(0,self.model.rowCount()); self.detail.setText('No current result'); self.filter.clear()
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

    @Slot(object,object,object,object)
    def scan_succeeded(self,dates,result,matches,capture=None):
        self.scan_capture=capture
        if self._token is not None and self._token.is_set(): self.scan_cancelled(); return
        self.snapshot=(self.scan_request,tuple(dates),result,tuple(matches)); self.show_live(dates,result,matches); self.progress.setRange(0,100); self.progress.setValue(100); self.cancel.setEnabled(False); self.scan_completed=utc(); self.scan_uuid=str(uuid4()); self.save_current_scan()

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
        if self._report_thread is not None:
            event.ignore(); self.statusBar().showMessage("Report generation still running"); return
        if self._db_thread is not None:
            event.ignore(); self.statusBar().showMessage('Database operation still running'); return
        if self._history_thread is not None:
            event.ignore(); self.statusBar().showMessage('Historical simulation still running'); return
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
        self.statusBar().showMessage('Scan complete | Database save pending')

    def make_backtesting(self):
        _,layout=self.page('Backtesting'); form=QFormLayout(); layout.addLayout(form)
        self.years=QSpinBox(); self.years.setRange(1,10); self.years.setValue(2)
        self.holding=QSpinBox(); self.holding.setRange(1,250); self.holding.setValue(5)
        self.cost=QDoubleSpinBox(); self.cost.setRange(0,100); self.cost.setValue(.5); self.cost.setSuffix('%')
        for label,widget in [('History years',self.years),('Holding sessions',self.holding),('Round-trip cost',self.cost)]: form.addRow(label,widget)
        note=QLabel('Uses the last completed live scan and its original settings. Current candidate selection introduces survivorship and selection bias; not a point-in-time universe backtest.'); note.setWordWrap(True); layout.addWidget(note)
        self.backtest_button=QPushButton('Run historical simulation'); self.backtest_button.clicked.connect(self.start_history); layout.addWidget(self.backtest_button)
        self.history_status=QLabel('Complete a live scan first.'); self.history_status.setWordWrap(True); layout.addWidget(self.history_status); layout.addStretch()
    def make_reports(self):
        _,layout=self.page('Reports'); self.report_status=QLabel('Reports are saved in a separate V2 research folder.'); self.report_status.setWordWrap(True); layout.addWidget(self.report_status)
        self.export_button=QPushButton('Generate screening Word report'); self.export_button.clicked.connect(self.export_current); layout.addWidget(self.export_button)
        btn=QPushButton('Open reports folder'); btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.reports_dir())))); layout.addWidget(btn); layout.addStretch()
    def reports_dir(self):
        folder=Path.home()/'Nasdaq_Quant_Research_V2_Reports'; folder.mkdir(exist_ok=True); return folder
    def export_current(self):
        if self._report_thread is not None or self._db_thread is not None:
            self.report_status.setText('Report or database operation busy; retry when finished.'); return
        if self.snapshot is None or self._thread is not None or self._history_thread is not None:
            self.report_status.setText('A completed live scan is required.'); return
        snapshot=self.snapshot; uid=self.scan_uuid; directory=Path.home()/'Nasdaq_Quant_Research_V2_Reports'
        self.report_status.setText('Generating screening report in background…')
        for control in (self.export_button,self.backtest_button,self.live,self.run): control.setEnabled(False)
        self._report_thread=QThread(self); self._report_worker=DatabaseWorker(lambda:(uid,export_scan(snapshot,directory)[1])); self._report_worker.moveToThread(self._report_thread)
        self._report_thread.started.connect(self._report_worker.run)
        self._report_worker.succeeded.connect(self.report_generated)
        self._report_worker.failed.connect(self.report_failed)
        self._report_worker.finished.connect(self._report_thread.quit)
        self._report_worker.finished.connect(self._report_worker.deleteLater)
        self._report_thread.finished.connect(self.report_finished)
        self._report_thread.finished.connect(self._report_thread.deleteLater)
        self._report_thread.start()
    @Slot(object)
    def report_generated(self,value):
        uid,report=value; self.pending_report=(uid,report); self.report_status.setText(str(report)); self.save_pending_report()
    @Slot(str)
    def report_failed(self,message):
        self.report_status.setText('Report failed: '+message)
    @Slot()
    def report_finished(self):
        self._report_thread=None; self._report_worker=None
        for control in (self.export_button,self.backtest_button,self.live,self.run): control.setEnabled(True)
    def start_history(self):
        if self.snapshot is None or self._thread is not None or self._history_thread is not None or self._report_thread is not None:
            self.history_status.setText('A completed live scan is required.'); return
        if not self.snapshot[3]: self.history_status.setText('No qualifying tickers; simulation skipped.'); return
        if QMessageBox.question(self,'Historical simulation','Run historical research for the completed scan? The interface remains responsive; cancellation is not yet available for this operation.') != QMessageBox.StandardButton.Yes: return
        if self._db_thread is not None:
            self.history_status.setText('Database operation busy; retry when finished.'); return
        args=(self.snapshot,Path.home()/'Nasdaq_Quant_Research_V2_Reports',self.years.value(),self.holding.value(),self.cost.value())
        self.history_status.setText('Preparing report and historical simulation in background…'); self.history_context=(self.scan_uuid,utc(),str(uuid4()))
        for control in (self.backtest_button,self.export_button,self.live,self.run): control.setEnabled(False)
        self._history_thread=QThread(self); self._history_worker=HistoricalWorker(*args); self._history_worker.moveToThread(self._history_thread)
        self._history_thread.started.connect(self._history_worker.run); self._history_worker.succeeded.connect(self.history_done); self._history_worker.failed.connect(self.history_failed); self._history_worker.finished.connect(self._history_thread.quit); self._history_worker.finished.connect(self._history_worker.deleteLater); self._history_thread.finished.connect(self.history_finished); self._history_thread.finished.connect(self._history_thread.deleteLater); self._history_thread.start()
    @Slot(object,object,object,object)
    def history_done(self,result,path,screen,capture=None):
        if result.backtest is None: self.history_status.setText('No historical simulation performed.'); return
        sim=result.backtest.analysis.simulation
        self.history_status.setText(f'Historical period: {result.start_date} through {result.end_date} | Signals: {sim.total_signals} | Completed trades: {len(sim.trades)}\nIntegrated report: {path}')
        self.report_status.setText(str(path)); uid,started,run_uuid=self.history_context; self.pending_history=(uid,result,path,screen,started,utc(),run_uuid,capture); self.save_pending_history()
    @Slot(str)
    def history_failed(self,message): self.history_status.setText('Historical simulation/report failed: '+message+' — any completed local files are retained.')
    @Slot()
    def history_finished(self):
        self._history_thread=None; self._history_worker=None
        for control in (self.backtest_button,self.export_button,self.live,self.run): control.setEnabled(True)

    def make_research_history(self):
        _,layout=self.page('Research History'); self.db_status=QLabel('Connect in Settings. Saved screening outputs are not complete replayable snapshots.'); self.db_status.setWordWrap(True); layout.addWidget(self.db_status)
        self.history_list=QListWidget(); layout.addWidget(self.history_list,1)
        self.history_table=QTableWidget(0,10); self.history_table.setHorizontalHeaderLabels(['Ticker','Close','Gain %','Score','MACD','Histogram','Rising days','RSI','RVOL','Median dollar volume']); layout.addWidget(self.history_table,2)
        for title,callback in [('Refresh saved scans',self.refresh_saved),('View selected scan',self.load_saved),('Save current live scan',self.save_current_scan),('Save latest simulation',self.save_pending_history),('Save latest screening report',self.save_pending_report),('View saved simulations',self.view_simulations)]:
            btn=QPushButton(title); btn.clicked.connect(callback); layout.addWidget(btn)
    def make_database_settings(self):
        _,layout=self.page('Settings'); self.connection_label=QLabel('MySQL disconnected. Password held in memory only.'); layout.addWidget(self.connection_label)
        self.db_port=QSpinBox(); self.db_port.setRange(1,65535); self.db_port.setValue(3306); layout.addWidget(QLabel('Local MySQL port')); layout.addWidget(self.db_port)
        btn=QPushButton('Connect to research database'); btn.clicked.connect(self.connect_database); layout.addWidget(btn); layout.addStretch()
    def connect_database(self):
        if self._db_thread is not None: return
        password,ok=QInputDialog.getText(self,'MySQL','Password for nasdaq_research_app:',QLineEdit.EchoMode.Password)
        if not ok: return
        repo=Repository(password,self.db_port.value()); self.db_job(lambda:repo.history(),lambda rows:self.connected(repo,rows))
    def connected(self,repo,rows):
        self.repo=repo; self.connection_label.setText('Connected: nasdaq_quant_research_v2'); self.banner.setText('LIVE SCREENING • MySQL connected • Research inputs archived for new runs; replay not verified'); self.fill_history(rows); self.statusBar().showMessage('MySQL connected')
    def db_job(self,fn,done):
        if self._db_thread is not None: self.db_status.setText('Database operation busy; retry when finished.'); return
        self._db_thread=QThread(self); self._db_worker=DatabaseWorker(fn); self._db_worker.moveToThread(self._db_thread); self._db_done=done
        self._db_thread.started.connect(self._db_worker.run); self._db_worker.succeeded.connect(self.db_success); self._db_worker.failed.connect(self.db_failed); self._db_worker.finished.connect(self._db_thread.quit); self._db_worker.finished.connect(self._db_worker.deleteLater); self._db_thread.finished.connect(self.db_finished); self._db_thread.finished.connect(self._db_thread.deleteLater); self._db_thread.start()
    @Slot(object)
    def db_success(self,value): self._db_done(value)
    @Slot(str)
    def db_failed(self,message): self.db_status.setText('Database operation failed: '+message+' — current research retained.'); self.statusBar().showMessage('Database operation failed; see Research History')
    @Slot()
    def db_finished(self): self._db_thread=None; self._db_worker=None; self._db_done=None
    def fill_history(self,rows):
        self.history_list.clear()
        for row in rows: self.history_list.addItem(f'{row[0]} | {row[1]} | ${row[2]:g}–${row[3]:g} | Gain {row[4]:g}% | '+('Strict' if row[5] else 'Research')+f' | {row[6]} matches')
        self.db_status.setText(f'{len(rows)} saved scans (latest 500). Older runs may have outputs only.')
    def refresh_saved(self):
        if self.repo is None: self.db_status.setText('Connect in Settings first.'); return
        self.db_job(self.repo.history,self.fill_history)
    def load_saved(self):
        item=self.history_list.currentItem()
        if self.repo is None or item is None: return
        run_id=int(item.text().split('|')[0]); self.db_job(lambda:self.repo.results(run_id),self.fill_saved_results)
    def fill_saved_results(self,rows):
        self.history_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,val in enumerate(row): self.history_table.setItem(i,j,QTableWidgetItem(display_text(j,val)))
    def save_current_scan(self):
        if self.repo is None: self.db_status.setText('Not connected; live scan retained in memory only. Connect and use Save current live scan.'); return
        if self.snapshot is None or not hasattr(self,'scan_uuid'): return
        if self.saved_uuid==self.scan_uuid: self.db_status.setText('Current scan already saved.'); return
        snap=self.snapshot; uid=self.scan_uuid; started=self.scan_started; finished=self.scan_completed; repo=self.repo; capture=getattr(self,"scan_capture",None)
        self.db_job(lambda:repo.save_scan(snap,started,finished,uid,capture),lambda run:self.scan_saved(run,uid))
    def save_pending_report(self):
        if self.repo is None or not hasattr(self,'pending_report'):
            self.report_message('Connect and generate a screening report first.'); return
        if self._db_thread is not None:
            self.report_message('Database busy; retry Save latest screening report.'); return
        args=self.pending_report; repo=self.repo
        self.report_message('Saving screening report to MySQL…')
        self.db_job(lambda:repo.save_report(*args),lambda value:self.report_message(f'Screening report saved to MySQL: run {value[0]}' if value[1] else f'Screening report already recorded: run {value[0]}; new local file retained'))
    def report_message(self,message):
        self.report_status.setText(message); self.db_status.setText(message); self.statusBar().showMessage(message)
    def save_pending_history(self):
        if self.repo is None or not hasattr(self,'pending_history'): self.db_status.setText('Connect and complete a historical simulation first.'); return
        args=self.pending_history; repo=self.repo
        self.db_job(lambda:repo.save_history(*args),lambda run:self.db_status.setText(f'Historical outputs saved: run {run}. Replay not verified.'))
    def view_simulations(self):
        item=self.history_list.currentItem()
        if self.repo is None or item is None:
            self.db_status.setText('Connect and select a saved screening run first.'); return
        run=int(item.text().split('|')[0]); repo=self.repo
        self.db_job(lambda:(repo.simulations_for_run(run),repo.screening_report_count(run),repo.capture_counts(run)),self.show_saved_simulations)
    def show_saved_simulations(self,value):
        rows,count,artifacts=value
        self.db_status.setText('Saved simulations: '+('; '.join(f'run {r[0]}: {r[1]} signals, {r[2]} trades, {r[3]} reports' for r in rows) or 'none')+f' | Screening report records: {count} | Input artifact chunks: '+', '.join(f'run {r}: {n}' for r,n in artifacts))
    def scan_saved(self,run,uid):
        self.saved_uuid=uid; self.db_status.setText(f'Screening outputs saved: run {run}. Refresh saved scans to view.'); self.statusBar().showMessage(f'Screening outputs saved: run {run}')

class DatabaseWorker(QObject):
    succeeded=Signal(object); failed=Signal(str); finished=Signal()
    def __init__(self,fn): super().__init__(); self.fn=fn
    @Slot()
    def run(self):
        try: self.succeeded.emit(self.fn())
        except Exception as exc: self.failed.emit(str(exc))
        finally: self.finished.emit()
