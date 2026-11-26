"""Historical research through the validated V1.2 interfaces."""
from pathlib import Path
from uuid import uuid4
import json
from ..infrastructure.legacy_adapter import engine
from Backtesting_Engine.screener_handoff import load_screener_handoff
from .strict_capture import run_screener_backtest
from Backtesting_Engine.scored_screener_integration import run_scored_screener_backtest
from Backtesting_Engine.integrated_report import generate_integrated_report
from Backtesting_Engine.scored_integrated_report import generate_scored_integrated_report

def export_scan(snapshot, directory, years=2, holding=5, cost=.5):
    request, dates, result, matches = snapshot
    folder=Path(directory)/uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    payload=dict(schema_version=1,scan_id=folder.name,scan_date=dates[-1].isoformat(),qualifying_tickers=[m.security.ticker for m in matches],screener_settings=dict(min_gain_pct=request.gain,min_price=request.minimum,max_price=request.maximum,momentum_confirmation_required=request.strict),backtest_settings=dict(history_years=years,holding_sessions=holding,round_trip_cost_pct=cost))
    handoff=folder/'handoff.json'
    handoff.write_text(json.dumps(payload,indent=2,allow_nan=False),encoding='utf-8')
    h=load_screener_handoff(handoff)
    report=folder/'screening.docx'
    engine.build_document(report,matches,dates,result.checked,result.missing,request.gain,request.minimum,request.maximum,excluded_reverse=result.excluded_reverse,excluded_unverified=result.excluded_unverified,preliminary_matches=result.initial_matches,momentum_only=request.strict,excluded_momentum=result.excluded_momentum)
    return h, report

def historical(h, report):
    strict=h.screener_settings.momentum_confirmation_required
    result=(run_screener_backtest if strict else run_scored_screener_backtest)(h)
    if result.backtest is None:
        return result,None
    path=(generate_integrated_report if strict else generate_scored_integrated_report)(result,report,output_dir=report.parent)
    return result,path
