"""Version 1.2 Step 7 offline tests — no live Nasdaq scan or market downloads.

Run from Nasdaq_Quant_Research project root:
    py tests\\Step7_Integration_Tests.py
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
import importlib.util
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import pandas as pd
from docx import Document

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Market-data calls in this suite are mocked. Permit isolated test machines
# without yfinance; on the user's Windows installation this package exists.
if importlib.util.find_spec('yfinance') is None:
    sys.modules['yfinance'] = types.ModuleType('yfinance')

from Backtesting_Engine.screener_handoff import (
    BacktestSettings, ScreenerHandoff, ScreenerSettings,
)
from Backtesting_Engine.scored_backtest import ScorePerformance
from Backtesting_Engine import scored_screener_integration as integration
from Backtesting_Engine.scored_integrated_report import generate_scored_integrated_report
from Stock_Screener.Nasdaq_21_Session_Screener import offer_historical_backtest


def handoff(*, strict=False, tickers=('ANTX','ENTX'), day=date(2026,11,20)):
    return ScreenerHandoff(1, 'test_20261120', day, tickers,
        ScreenerSettings(10.0, 1.0, 10.0, strict),
        BacktestSettings(2, 5, 0.5),
        Path('sample.json'))


def fake_result(*, trades=True, excluded=False):
    h = handoff()
    signal = types.SimpleNamespace(ticker='ANTX', signal_date=date(2026,10,1))
    assessment = types.SimpleNamespace(score=4)
    scored_signals = (types.SimpleNamespace(signal=signal,assessment=assessment),)
    trade = types.SimpleNamespace(ticker='ANTX', signal_date=signal.signal_date,
                 entry_date=date(2026,10,2), exit_date=date(2026,10,8), net_return_pct=2.75)
    sim_trades = (trade,) if trades else ()
    sim = types.SimpleNamespace(total_signals=1, trades=sim_trades,
              skipped_overlapping=0, skipped_incomplete=0 if trades else 1)
    stats = types.SimpleNamespace(win_rate_pct=100.0, expectancy_pct=2.75,
                                  profit_factor=float('inf'))
    groups = tuple(ScorePerformance(s, 1 if s==4 else 0,
              1 if s==4 and trades else 0,
              stats if s==4 and trades else None) for s in (5,4,3,2,1,0,None))
    backtest=types.SimpleNamespace(analysis=types.SimpleNamespace(simulation=sim),
                analyzed_tickers=('ANTX',),
                excluded_tickers=(('ENTX','Historical coverage is incomplete'),) if excluded else (),
                scored_signals=scored_signals, score_groups=groups)
    return integration.ScoredScreenerRun(h, date(2024,11,20), h.scan_date,
                   (date(2026,10,1),date(2026,10,2)), backtest)


def create_screen(path, tickers=('ANTX','ENTX')):
    doc=Document()
    doc.add_paragraph('NASDAQ 21-SESSION STOCK SCREEN')
    doc.add_paragraph('Observation dates: Oct 23, 2026 - Nov 20, 2026')
    table=doc.add_table(rows=1,cols=2)
    table.rows[0].cells[0].text='Symbol'
    table.rows[0].cells[1].text='Description'
    for symbol in tickers:
        row=table.add_row()
        row.cells[0].text=symbol
        row.cells[1].text='Sample'
    doc.save(path)


class Step7Tests(unittest.TestCase):
    def test_01_unattended_mode_never_prompts(self):
        with patch('builtins.input', side_effect=AssertionError('prompt not allowed')):
            offer_historical_backtest(Path('a.json'),no_prompt=True,
                  qualifying_count=2, momentum_only=False)

    def test_02_zero_candidates_skips_without_prompt(self):
        with patch('builtins.input', side_effect=AssertionError('prompt not allowed')):
            offer_historical_backtest(Path('a.json'),no_prompt=False,
                  qualifying_count=0,momentum_only=False)

    def test_03_missing_handoff_skips(self):
        with patch('builtins.input', side_effect=AssertionError('prompt not allowed')):
            offer_historical_backtest(None,no_prompt=False,
                  qualifying_count=2,momentum_only=False)

    def test_04_enter_defaults_no_for_discovery(self):
        with patch('builtins.input', return_value=''), patch.object(integration, 'main') as run:
            offer_historical_backtest(Path('a.json'),no_prompt=False,
                  qualifying_count=2,momentum_only=False)
            run.assert_not_called()

    def test_05_discovery_y_launches_scored_only(self):
        from Backtesting_Engine import screener_backtest
        with patch('builtins.input',return_value='y'),\
             patch.object(integration, 'main', return_value=0) as scored,\
             patch.object(screener_backtest, 'main',return_value=0) as strict:
            offer_historical_backtest(Path('a.json'),no_prompt=False,
                  qualifying_count=2,momentum_only=False,screener_report_path=Path('r.docx'))
            scored.assert_called_once_with(['a.json','--screener-report','r.docx'])
            strict.assert_not_called()

    def test_06_strict_y_preserves_old_launcher(self):
        from Backtesting_Engine import screener_backtest
        with patch('builtins.input',return_value='yes'),\
             patch.object(integration, 'main',return_value=0) as scored,\
             patch.object(screener_backtest, 'main',return_value=0) as strict:
            offer_historical_backtest(Path('a.json'),no_prompt=False,
                  qualifying_count=2,momentum_only=True,screener_report_path=Path('r.docx'))
            strict.assert_called_once_with(['a.json','--screener-report','r.docx'])
            scored.assert_not_called()

    def test_07_invalid_reply_reprompts(self):
        with patch('builtins.input', side_effect=['wrong','n']) as answers,\
             patch.object(integration,'main') as scored:
            offer_historical_backtest(Path('a.json'),no_prompt=False,
                  qualifying_count=2,momentum_only=False)
            self.assertEqual(answers.call_count,2)
            scored.assert_not_called()

    def test_08_backtest_failure_does_not_fail_screen(self):
        stderr=StringIO()
        with patch('builtins.input',return_value='y'),\
             patch.object(integration,'main',return_value=1), redirect_stderr(stderr):
            offer_historical_backtest(Path('a.json'),no_prompt=False,
                  qualifying_count=2,momentum_only=False)
        self.assertIn('original Word screening report is unaffected',stderr.getvalue())

    def test_09_scored_runner_rejects_strict_handoff(self):
        with self.assertRaises(integration.HandoffBacktestError):
            integration.run_scored_screener_backtest(handoff(strict=True))

    def test_10_scored_runner_empty_handoff_skips_data_access(self):
        with patch('Backtesting_Engine.market_data_provider.download_historical_prices') as load:
            result=integration.run_scored_screener_backtest(handoff(tickers=()))
        self.assertIsNone(result.backtest)
        load.assert_not_called()

    def test_11_scored_runner_preserves_settings_and_calendar_bounds(self):
        from Backtesting_Engine import scored_backtest
        from Backtesting_Engine import market_data_provider
        cal=pd.DataFrame({'Close':1.0},index=pd.bdate_range('2024-11-20','2026-11-20'))
        with patch.object(market_data_provider,'download_historical_prices',return_value=cal) as load,\
             patch.object(scored_backtest,'run_scored_multi_stock_backtest',return_value=object()) as run:
            result=integration.run_scored_screener_backtest(handoff())
        self.assertEqual(result.start_date,date(2024,11,20))
        self.assertEqual(result.trading_dates[0],date(2024,11,20))
        self.assertEqual(result.trading_dates[-1],date(2026,11,20))
        self.assertEqual(load.call_args.args,('QQQ',date(2024,11,20),date(2026,11,20)))
        k=run.call_args.kwargs
        self.assertEqual(k['tickers'],('ANTX','ENTX'))
        self.assertEqual((k['min_gain_pct'],k['min_price'],k['max_price']),(10.0,1.0,10.0))
        self.assertEqual((k['holding_sessions'],k['round_trip_cost_pct']),(5,0.5))
        self.assertEqual((k['start_date'],k['end_date']), (result.trading_dates[0],result.trading_dates[-1]))

    def test_12_reference_calendar_must_be_sufficient(self):
        from Backtesting_Engine import market_data_provider
        cal=pd.DataFrame({'Close':[1.0]*9},index=pd.bdate_range('2026-11-02',periods=9))
        with patch.object(market_data_provider,'download_historical_prices',return_value=cal):
            with self.assertRaises(integration.HandoffBacktestError):
                integration.run_scored_screener_backtest(handoff())

    def test_13_scored_report_contents_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.docx'
            create_screen(source)
            original=source.read_bytes()
            path=generate_scored_integrated_report(fake_result(excluded=True),source, output_dir=Path(d)/'Reports')
            self.assertTrue(path.is_file())
            self.assertEqual(source.read_bytes(),original)
            doc=Document(path)
            text='\n'.join(p.text for p in doc.paragraphs)
            self.assertIn('HISTORICAL SCORE-BASED BACKTESTING ANALYSIS',text)
            self.assertIn('Historical Performance by Signal-Date Technical Score',text)
            self.assertIn('Historical Data Exclusions',text)
            self.assertIn('Limitations and Interpretation',text)
            tables='\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
            self.assertIn('4/5',tables)
            self.assertIn('+2.7500%',tables)
            self.assertIn('Historical coverage is incomplete',tables)

    def test_14_no_trades_show_na_not_zero_win_rate(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.docx'
            create_screen(source)
            path=generate_scored_integrated_report(fake_result(trades=False),source,output_dir=Path(d))
            doc=Document(path)
            text='\n'.join(p.text for p in doc.paragraphs)
            tables='\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
            self.assertIn('No completed simulated trades',text)
            self.assertIn('N/A',tables)

    def test_15_mismatched_word_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.docx'
            create_screen(source, tickers=('ANTX',))
            with self.assertRaises(ValueError):
                generate_scored_integrated_report(fake_result(),source,output_dir=Path(d))

    def test_16_same_scan_reports_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.docx'
            create_screen(source)
            first=generate_scored_integrated_report(fake_result(),source,output_dir=Path(d))
            second=generate_scored_integrated_report(fake_result(),source,output_dir=Path(d))
            self.assertNotEqual(first,second)
            self.assertTrue(first.is_file() and second.is_file())

    def test_17_integrated_report_with_missing_source_fails_safely(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                generate_scored_integrated_report(fake_result(),Path(d)/'missing.docx')


    def test_18_generated_trade_table_header_repeats_on_new_pages(self):
        from docx.oxml.ns import qn
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'source.docx'
            create_screen(source)
            report = generate_scored_integrated_report(fake_result(), source, output_dir=Path(d))
            doc = Document(report)
            trade_tables = [
                table for table in doc.tables
                if table.rows
                and tuple(cell.text for cell in table.rows[0].cells) ==
                ('Ticker', 'Signal date', 'Historical score',
                 'Entry date', 'Exit date', 'Net return')
            ]
            self.assertEqual(len(trade_tables), 1)
            tr_properties = trade_tables[0].rows[0]._tr.get_or_add_trPr()
            self.assertIsNotNone(tr_properties.find(qn('w:tblHeader')))


if __name__ == '__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Step7Tests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        print('SUCCESS: ALL 18 STEP 7 OFFLINE TESTS PASSED.')
    sys.exit(not result.wasSuccessful())
