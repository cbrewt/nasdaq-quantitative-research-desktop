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
