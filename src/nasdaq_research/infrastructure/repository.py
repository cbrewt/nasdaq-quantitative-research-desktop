"""Transactional persistence of completed screening outputs (not raw provider inputs)."""
import math, json, platform, sys
from datetime import datetime, timezone
from uuid import uuid4
from contextlib import contextmanager
from ..application.screening import number

FLAGS=('macd_positive','histogram_positive','histogram_rising_three','rsi_50_to_70','relative_volume_above_one')
COLS=('Open','High','Low','Close','Volume','MACD','Signal','Histogram','NormalizedHistogram','RSI','RelativeVolume','RisingDays')
def utc(): return datetime.now(timezone.utc).replace(tzinfo=None)
class Repository:
    def __init__(self,password,port=3306): self._password=password; self.port=port
    @contextmanager
    def connection(self):
        import mysql.connector
        cn=mysql.connector.connect(host='127.0.0.1',port=self.port,user='nasdaq_research_app',password=self._password,database='nasdaq_quant_research_v2',connection_timeout=10,autocommit=False)
        try:
            yield cn
            cn.commit()
        except BaseException:
            cn.rollback(); raise
        finally: cn.close()
    def history(self):
        with self.connection() as cn:
            cur=cn.cursor(); cur.execute("SELECT r.run_id,s.scan_date,s.min_price,s.max_price,s.min_gain_pct,s.momentum_required,(SELECT COUNT(*) FROM screening_result x WHERE x.run_id=r.run_id) FROM research_run r JOIN screening_run s ON s.run_id=r.run_id WHERE r.status='COMPLETED' ORDER BY r.run_id DESC LIMIT 500")
            return cur.fetchall()
    def results(self,run_id):
        with self.connection() as cn:
            cur=cn.cursor(); cur.execute("SELECT u.ticker,s.last_close,s.gain_pct,s.technical_score,d.macd,d.histogram,d.rising_days,d.rsi,d.relative_volume,s.median_dollar_volume FROM screening_result s JOIN run_security u ON u.run_id=s.run_id AND u.security_id=s.security_id JOIN screening_run a ON a.run_id=s.run_id LEFT JOIN daily_observation d ON d.run_id=s.run_id AND d.security_id=s.security_id AND d.series_kind='SCREEN_DISPLAY' AND d.session_date=a.scan_date WHERE s.run_id=%s ORDER BY s.report_rank",(run_id,)); return cur.fetchall()
    def save_scan(self,snapshot,started,finished,scan_uuid):
        request,dates,result,matches=snapshot
        with self.connection() as cn:
            cur=cn.cursor()
            def insert(table,columns,values):
                cur.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join(['%s']*len(columns))+')',tuple(values)); return cur.lastrowid
            run=insert('research_run',('run_uuid','run_kind','started_utc','finished_utc','status','engine_revision','environment_json'),(scan_uuid,'SCAN',started,finished,'COMPLETED','V1.2 validated / V2 Step 10',json.dumps({'python':sys.version,'platform':platform.platform(),'input_capture':'qualified display observations only; not replayable','history_defaults':'2 years, 5 sessions, 0.50%'})))
            insert('screening_run',('run_id','scan_id','scan_date','min_gain_pct','min_price','max_price','momentum_required','batch_size','batch_delay_seconds','retries','history_years','holding_sessions','round_trip_cost_pct','checked','missing','initial_matches','excluded_reverse','excluded_unverified','excluded_momentum'),(run,scan_uuid,dates[-1],request.gain,request.minimum,request.maximum,int(request.strict),50,1.25,2,2,5,.5,result.checked,result.missing,result.initial_matches,result.excluded_reverse,result.excluded_unverified,result.excluded_momentum))
            for i,d in enumerate(dates,1): insert('trading_session',('run_id','session_date','session_no'),(run,d,i))
            ranks={m.security.ticker:i for i,m in enumerate(result.matches,1)}
            for rank,m in enumerate(matches,1):
                sid=insert('security',('identity_note',),('Run-local identity; ticker continuity not inferred',))
                insert('run_security',('run_id','security_id','ticker','security_name','disposition'),(run,sid,m.security.ticker,m.security.name,'QUALIFIED'))
                score=m.technical_score
                insert('screening_result',('run_id','security_id','gain_pct','avg_open','avg_close','avg_volume','first_close','last_close','median_dollar_volume','scan_rank','report_rank','technical_score',*FLAGS),(run,sid,m.gain_pct,m.avg_open,m.avg_close,m.avg_volume,m.first_close,m.last_close,number(m.median_daily_dollar_volume),ranks[m.security.ticker],rank,score.score,*(None if score.conditions[k] is None else int(score.conditions[k]) for k in FLAGS)))
                for d,row in m.daily.iterrows():
                    vals=[number(row.get(k)) for k in COLS]; vals[-1]=None if vals[-1] is None else int(vals[-1])
                    insert('daily_observation',('run_id','security_id','series_kind','session_date','open_price','high_price','low_price','close_price','volume','macd','signal_line','histogram','normalized_histogram','rsi','relative_volume','rising_days'),(run,sid,'SCREEN_DISPLAY',str(d)[:10],*vals))
            return run

    def _source_run(self,cur,uid):
        cur.execute("SELECT run_id FROM screening_run WHERE scan_id=%s",(uid,))
        row=cur.fetchone()
        if row is None: raise ValueError('Save the source screening run first.')
        return row[0]
    def _insert_report(self,cur,run,path,kind):
        from pathlib import Path
        import hashlib
        p=Path(path); payload=p.read_bytes(); sha=hashlib.sha256(payload).hexdigest()
        cur.execute('SELECT report_id FROM research_report WHERE run_id=%s AND sha256=%s AND report_kind=%s',(run,sha,kind))
        if cur.fetchone(): return
        cur.execute('INSERT INTO research_report (run_id,report_kind,generated_utc,filename,sha256,payload) VALUES (%s,%s,%s,%s,%s,%s)',(run,kind,utc(),p.name,sha,payload))
    def save_report(self,uid,path):
        with self.connection() as cn:
            cur=cn.cursor(); run=self._source_run(cur,uid); self._insert_report(cur,run,path,'SCREENING'); return run
    def save_history(self,uid,result,path,screen_report,started,finished,run_uuid):
        h=result.handoff; b=result.backtest; sim=b.analysis.simulation
        if not hasattr(b,'scored_signals'): raise ValueError('Strict-mode result does not expose all historical signals; report retained locally, not saved as a complete simulation.')
        scored=b.scored_signals; trades={(t.ticker,t.signal_date):t for t in sim.trades}
        keys={(s.signal.ticker,s.signal.signal_date) for s in scored}
        if len(keys)!=len(scored) or len(scored)!=sim.total_signals or not set(trades)<=keys: raise ValueError('Historical signal accounting mismatch')
        with self.connection() as cn:
            cur=cn.cursor(); source=self._source_run(cur,uid)
            cur.execute('SELECT run_id FROM research_run WHERE run_uuid=%s',(run_uuid,)); existing=cur.fetchone()
            if existing: return existing[0]
            def ins(table,cols,vals):
                cur.execute('INSERT INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join(['%s']*len(cols))+')',tuple(vals)); return cur.lastrowid
            run=ins('research_run',('run_uuid','run_kind','started_utc','finished_utc','status','engine_revision','environment_json'),(run_uuid,'BACKTEST',started,finished,'COMPLETED','V1.2 validated / V2 Step 10',json.dumps({'input_capture':'historical outputs only; not replayable','skipped_disposition':'UNKNOWN for noncompleted signals; aggregate counts retained'})))
            s=h.screener_settings; p=h.backtest_settings
            ins('backtest_run',('run_id','source_scan_run_id','history_years','evaluation_start','evaluation_end','min_gain_pct','min_price','max_price','momentum_required','holding_sessions','round_trip_cost_pct','total_signals','skipped_overlapping','skipped_incomplete'),(run,source,p.history_years,result.start_date,result.end_date,s.min_gain_pct,s.min_price,s.max_price,int(s.momentum_confirmation_required),p.holding_sessions,p.round_trip_cost_pct,sim.total_signals,sim.skipped_overlapping,sim.skipped_incomplete))
            for i,d in enumerate(result.trading_dates,1): ins('trading_session',('run_id','session_date','session_no'),(run,d,i))
            cur.execute('SELECT ticker,security_id FROM run_security WHERE run_id=%s',(source,)); ids=dict(cur.fetchall())
            exclusions=dict(b.excluded_tickers); counts=dict(b.signal_counts)
            for ticker in b.requested_tickers:
                ins('run_security',('run_id','security_id','ticker','disposition','reason','signal_count'),(run,ids[ticker],ticker,'EXCLUDED' if ticker in exclusions else 'ANALYZED',exclusions.get(ticker),counts.get(ticker)))
            for item in scored:
                a=item.assessment; s=item.signal; key=(s.ticker,s.signal_date)
                ins('historical_signal',('run_id','security_id','signal_date','first_close','last_close','gain_pct','macd','histogram','rsi','relative_volume','rising_days','technical_score',*FLAGS,'trade_disposition'),(run,ids[s.ticker],s.signal_date,*(number(getattr(s,k)) for k in ('first_close','last_close','gain_pct','macd','histogram','rsi','relative_volume')),None if number(s.rising_days) is None else int(s.rising_days),a.score,*(None if a.conditions[k] is None else int(a.conditions[k]) for k in FLAGS),'COMPLETED' if key in trades else 'UNKNOWN'))
            fields=('entry_date','exit_date','holding_sessions','entry_price','exit_price','gross_return_pct','round_trip_cost_pct','net_return_pct')
            for t in sim.trades: ins('simulated_trade',('run_id','security_id','signal_date',*fields),(run,ids[t.ticker],t.signal_date,*(getattr(t,k) for k in fields)))
            fields=('total_trades','winning_trades','losing_trades','breakeven_trades','win_rate_pct','average_gross_return_pct','average_net_return_pct','average_winning_return_pct','average_losing_return_pct','expectancy_pct','profit_factor','best_trade_pct','worst_trade_pct','average_transaction_cost_pct')
            for group,count,stats in [('ALL',sim.total_signals,b.analysis.statistics)]+[(str(g.score) if g.score is not None else 'NA',g.signal_count,g.statistics) for g in b.score_groups]:
                pf=None if stats is None else stats.profit_factor
                vals=[getattr(stats,k) if stats is not None else (0 if i<4 else None) for i,k in enumerate(fields)]
                vals[10]=number(pf)
                ins('performance_summary',('run_id','score_group','signal_count',*fields,'profit_factor_state'),(run,group,count,*vals,'UNDEFINED' if pf is None else ('INFINITE' if math.isinf(pf) else 'FINITE')))
            self._insert_report(cur,source,screen_report,'SCREENING')
            if path is not None: self._insert_report(cur,run,path,'INTEGRATED')
            return run
    def history_simulations(self,uid):
        with self.connection() as cn:
            cur=cn.cursor(); source=self._source_run(cur,uid)
            cur.execute('SELECT b.run_id,b.total_signals,COUNT(t.signal_date) FROM backtest_run b LEFT JOIN simulated_trade t ON t.run_id=b.run_id WHERE b.source_scan_run_id=%s GROUP BY b.run_id,b.total_signals ORDER BY b.run_id DESC',(source,)); return cur.fetchall()

    def simulations_for_run(self,source):
        with self.connection() as cn:
            cur=cn.cursor(); cur.execute('SELECT b.run_id,b.total_signals,(SELECT COUNT(*) FROM simulated_trade t WHERE t.run_id=b.run_id),(SELECT COUNT(*) FROM research_report r WHERE r.run_id=b.run_id) FROM backtest_run b WHERE b.source_scan_run_id=%s ORDER BY b.run_id DESC',(source,)); return cur.fetchall()
