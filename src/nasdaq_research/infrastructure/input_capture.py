"""Capture exact provider-level numeric inputs; never deserialize executable objects."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
import base64, gzip, hashlib, io, json, platform, sys
import importlib.metadata as metadata
import numpy as np
import pandas as pd

_LOCK = Lock()

def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'), default=str).encode('utf-8')

def encode_frame(frame):
    if not isinstance(frame, pd.DataFrame):
        raise TypeError('Expected provider DataFrame')
    def axis(index):
        if isinstance(index, pd.DatetimeIndex):
            return dict(kind='datetime', values=[x.isoformat() for x in index], tz=str(index.tz) if index.tz else None, name=index.name)
        if isinstance(index, pd.MultiIndex):
            return dict(kind='multi', names=list(index.names), levels=[list(x) for x in index.levels], codes=[list(map(int,x)) for x in index.codes])
        if isinstance(index, pd.RangeIndex):
            return dict(kind='range',start=index.start,stop=index.stop,step=index.step,name=index.name)
        return dict(kind='plain', values=index.tolist(), name=index.name)
    columns=[]
    for i in range(len(frame.columns)):
        a=frame.iloc[:,i].to_numpy(copy=True)
        if a.dtype.kind not in 'biufcMm':
            raise TypeError(f'Unsupported provider dtype: {a.dtype}')
        b=io.BytesIO(); np.save(b,a,allow_pickle=False)
        columns.append(base64.b64encode(b.getvalue()).decode('ascii'))
    return json_bytes(dict(index=axis(frame.index), columns=axis(frame.columns), arrays=columns))

def decode_frame(payload):
    data=json.loads(payload)
    def axis(a):
        k=a['kind']
        if k=='datetime':
            if a['tz']:
                return pd.DatetimeIndex(pd.to_datetime(a['values'],utc=True,format='ISO8601')).tz_convert(a['tz']).rename(a['name'])
            return pd.DatetimeIndex(pd.to_datetime(a['values'],format='ISO8601')).rename(a['name'])
        if k=='multi':
            return pd.MultiIndex(levels=a['levels'],codes=a['codes'],names=a['names'])
        if k=='range': return pd.RangeIndex(a['start'],a['stop'],a['step'],name=a['name'])
        return pd.Index(a['values'],name=a['name'])
    index=axis(data['index']); columns=axis(data['columns'])
    values={i:np.load(io.BytesIO(base64.b64decode(v)),allow_pickle=False) for i,v in enumerate(data['arrays'])}
    result=pd.DataFrame(values,index=index); result.columns=columns
    return result

class Capture:
    def __init__(self,kind):
        self.kind=kind; self.records=[]; self.errors=[]
        root=Path(__file__).resolve().parents[1]
        code={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sorted(root.rglob('*.py'))}
        versions={n:metadata.version(n) for n in ('numpy','pandas','yfinance','requests','python-docx')}
        self.add('ENVIRONMENT','local',{},json_bytes(dict(python=sys.version,platform=platform.platform(),packages=versions,source_sha256=code)),'json')
    def add(self,role,provider,request,payload,fmt):
        self.records.append((role,provider,datetime.now(timezone.utc).replace(tzinfo=None),request,gzip.compress(payload,mtime=0),fmt))
    def safe(self,role,provider,request,value):
        try:
            if isinstance(value,pd.DataFrame):
                self.add(role,provider,request,encode_frame(value),'frame-npy-json-v1')
            elif value is None:
                self.add(role,provider,request,b'null','json')
            else: raise TypeError('Unexpected provider result type')
        except Exception as exc: self.errors.append(f'{role}: {type(exc).__name__}: {exc}')
    def call(self,role,provider,fn,args,kw,extra=None):
        request=dict(args=list(args),kwargs=kw,**(extra or {}))
        try: value=fn(*args,**kw)
        except Exception as exc:
            self.add(role,provider,request,json_bytes(dict(error_type=type(exc).__name__,message=str(exc))),'provider-error-json'); raise
        self.safe(role,provider,request,value); return value

class YahooProxy:
    def __init__(self,original,capture): self.original=original; self.capture=capture
    def __getattr__(self,key): return getattr(self.original,key)
    def download(self,*a,**kw): return self.capture.call('YAHOO_DOWNLOAD','Yahoo Finance',self.original.download,a,kw)
    def Ticker(self,symbol,*a,**kw):
        original=self.original.Ticker(symbol,*a,**kw); capture=self.capture
        class TickerProxy:
            def __getattr__(self,key): return getattr(original,key)
            def history(self,*args,**kwargs): return capture.call('YAHOO_HISTORY','Yahoo Finance',original.history,args,kwargs,{'ticker':symbol})
        return TickerProxy()

class DirectoryProxy:
    def __init__(self,original,capture): self.original=original; self.capture=capture
    def __getattr__(self,key): return getattr(self.original,key)
    def get(self,url,*a,**kw):
        response=self.original.get(url,*a,**kw)
        self.capture.add('NASDAQ_DIRECTORY','Nasdaq Trader',dict(url=url,status=response.status_code),response.content,'raw-bytes')
        return response

@contextmanager
def capturing(kind,engine,provider=None,listing_registry=None):
    """Replace only module references, not global third-party library functions."""
    with _LOCK:
        cap=Capture(kind); originals=[]
        def swap(obj,key,value):
            originals.append((obj,key,getattr(obj,key))); setattr(obj,key,value)
        try:
            if kind=='SCAN':
                swap(engine,'yf',YahooProxy(engine.yf,cap)); swap(engine,'requests',DirectoryProxy(engine.requests,cap))
                cutoff=engine.last_completed_calendar_date
                def recorded_cutoff(*a,**kw):
                    d=cutoff(*a,**kw); cap.add('SCAN_CUTOFF','local',{},json_bytes(d.isoformat()),'json'); return d
                swap(engine,'last_completed_calendar_date',recorded_cutoff)
            else:
                swap(provider,'yf',YahooProxy(provider.yf,cap))
                if listing_registry is not None: cap.add('LISTING_REGISTRY','local',{},json_bytes(listing_registry),'json')
            yield cap
        finally:
            for obj,key,value in reversed(originals): setattr(obj,key,value)

def store_capture(cur,run,cap):
    """Use existing schema; each compressed chunk has independent integrity hash."""
    if cap is None: return
    seq=0
    records=list(cap.records)
    records.append(('CAPTURE_MANIFEST','local',datetime.now(timezone.utc).replace(tzinfo=None),{},gzip.compress(json_bytes(dict(kind=cap.kind,records=len(records),errors=cap.errors)),mtime=0),'json'))
    for ordinal,(role,provider,stamp,request,payload,fmt) in enumerate(records,1):
        full_hash=hashlib.sha256(payload).hexdigest(); chunks=[payload[i:i+262144] for i in range(0,len(payload),262144)]
        for i,part in enumerate(chunks,1):
            seq+=1; info=dict(request=request,record=ordinal,chunk=i,chunks=len(chunks),compressed_sha256=full_hash)
            cur.execute('INSERT INTO input_artifact (run_id,role,sequence_no,provider,captured_utc,request_json,format_name,sha256,payload) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',(run,role,seq,provider,stamp,json_bytes(info).decode(),'gzip-'+fmt,hashlib.sha256(part).hexdigest(),part))
    cur.execute('SELECT sequence_no,sha256,payload FROM input_artifact WHERE run_id=%s ORDER BY sequence_no',(run,))
    count=0; valid=True
    for sequence,sha,payload in cur:
        count+=1
        if sequence!=count or hashlib.sha256(payload).hexdigest()!=sha: valid=False
    if not valid or count!=seq: raise RuntimeError('Input artifact readback integrity failure')
