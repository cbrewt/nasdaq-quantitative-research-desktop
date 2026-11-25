"""Explicit src-layout GUI entry point."""
import sys
from PySide6.QtWidgets import QApplication
from .presentation.main_window import Window, NAMES

def main():
    app=QApplication(sys.argv[:1]); window=Window()
    if '--smoke-test' in sys.argv:
        assert window.stack.count()==6
        for i in range(6):
            window.nav.setCurrentRow(i); assert window.stack.currentIndex()==i
        window.nav.setCurrentRow(0); window.preview(); assert window.model.rowCount()==4
        window.filter.setText('DEMO-B'); assert window.proxy.rowCount()==1
        window.open_analysis(window.proxy.index(0,0)); assert window.nav.currentRow()==1 and 'DEMO-B' in window.detail.text()
        window.filter.clear(); window.minimum.setValue(20); window.preview(); assert window.model.rowCount()==0 and 'Invalid' in window.summary.text()
        window.minimum.setValue(1); window.mode.setCurrentIndex(1); window.preview(); assert window.model.rowCount()==0 and 'unavailable' in window.summary.text()
        print('PASS: six workspaces, demo rows, ticker filter, row analysis, invalid range, strict-mode boundary')
        return 0
    window.show(); return app.exec()
