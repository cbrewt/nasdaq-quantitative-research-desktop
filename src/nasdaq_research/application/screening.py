"""Application-facing screening service; quantitative implementation delegated unchanged."""
from dataclasses import dataclass
import math
from ..infrastructure.legacy_adapter import engine

@dataclass(frozen=True)
class ScreeningRequest:
    minimum: float
    maximum: float
    gain: float
    strict: bool = False
    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.minimum,self.maximum,self.gain)) or not 0 < self.minimum <= self.maximum or self.gain < 0:
            raise ValueError('Invalid price range or gain: minimum price must be positive, maximum at least minimum, gain nonnegative.')

def screen(request):
    dates=engine.get_session_dates(engine.last_completed_calendar_date())
    symbols=engine.fetch_nasdaq_symbols()
    result=engine.scan(symbols,dates,50,1.25,2,request.gain,request.minimum,request.maximum,momentum_only=request.strict)
    matches=engine.rank_discovered_stocks(result.matches)
    return dates,result,matches

def display_row(match):
    latest=match.daily.iloc[-1]
    return (match.security.ticker,match.last_close,match.gain_pct,match.technical_score.score,latest.get('MACD'),latest.get('Histogram'),latest.get('RisingDays'),latest.get('RSI'),latest.get('RelativeVolume'),match.median_daily_dollar_volume)

def number(value):
    if value is None: return None
    try: return float(value) if math.isfinite(float(value)) else None
    except (ValueError,TypeError,OverflowError): return None
