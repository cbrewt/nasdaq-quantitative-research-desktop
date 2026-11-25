# Nasdaq Quantitative Research V2.0

## Quantitative Preservation Contract

Document reference: QPC-001
Approval date: November 25, 2026
Status: APPROVED
Implementation verification: PENDING
Development milestone: 02

### 1. Purpose

Preserve the mathematical integrity, research
methodology and quantitative behavior of the
validated Version 1.2 research engine.

The desktop interface shall not introduce changes
to existing research calculations.

### 2. Authoritative reference baseline

Archive:
Nasdaq_Quant_Research_V1_2_Validated_Source.zip

SHA-256:
71ec91441fe26f35e34534b5e758c01a4b8aacf2e75938aa156a4f78ef457909

Baseline selection: ADR-015
Architecture reference: ARCH-001
Engine preservation decision: ADR-018

The validated source implementation shall serve
as the quantitative reference for regression testing.

### 3. Approved preservation requirements

#### QPC-01 - Observation window

Preserve the existing twenty-one-session
screening observation window.

The gain calculation compares the first and
last closing prices within twenty-one observations,
representing twenty close-to-close intervals.

Do not silently change this convention.

#### QPC-02 - Price and percentage gain

Preserve existing price-range qualification,
inclusive price boundaries, gain calculations
and numerical tolerance behavior.

Percentage gain:

((Latest Close / First Close) - 1) * 100

Preserve existing default screening parameters:

- Minimum closing price: 1.00 USD.
- Maximum closing price: 10.00 USD.
- Minimum percentage gain: 10 percent.

#### QPC-03 - Reverse-split exclusion

Preserve the existing corporate-action review
and reverse-split exclusion methodology.

Securities with identified reverse splits or
unverifiable split histories shall continue
to be handled according to the validated
Version 1.2 implementation.

Disclose limitations of external corporate-action
data availability and completeness.

#### QPC-04 - Completed trading sessions

Preserve the existing completed-session cutoff,
reference calendar acquisition and trading-date
selection behavior.

Incomplete intraday observations shall not
be substituted for completed trading sessions.

#### QPC-05 - Technical indicator calculations

Preserve existing calculations for:

- MACD.
- MACD signal line.
- MACD histogram.
- Histogram change.
- Consecutive histogram increases.
- Normalized histogram.
- Relative Strength Index.
- Relative Volume.

Preserve the existing calculation parameters
and smoothing conventions.

MACD parameters: 12, 26 and 9.
RSI period: 14.
Relative volume baseline: previous 20 sessions.

#### QPC-06 - Warmup and missing data

Preserve existing indicator initialization,
minimum observation requirements and
missing-data handling.

The current session shall remain excluded
from its own historical relative volume baseline.

Do not manufacture indicator values when
the required historical observations are unavailable.

#### QPC-07 - Five-point technical scoring

Preserve the existing five scoring conditions:

1. MACD greater than zero.
2. MACD histogram greater than zero.
3. At least three consecutive histogram increases.
4. RSI between 50 and 70, inclusive.
5. Relative volume greater than 1.0.

Each satisfied condition contributes one point.

The maximum available technical score is five.

No scoring weights or thresholds shall be
modified without explicit user approval.

#### QPC-08 - Zero versus unavailable scores

A valid score of zero shall remain distinct
from an unavailable technical score.

Missing indicator values shall not be silently
converted to zero or treated as failed
conditions producing a valid total score.

Preserve the validated engine's unavailable-score
behavior in all application layers.

#### QPC-09 - Screening modes

Preserve Research Mode and Strict Momentum Mode.

Research Mode:

Technical characteristics are used for scoring
and ranking rather than mandatory momentum
qualification.

Strict Momentum Mode:

Existing mandatory momentum qualification
requirements remain in force.

Preserve existing command-line compatibility
and mode-selection behavior.

Desktop defaults require user interface approval.

#### QPC-10 - Liquidity and ranking

Preserve median daily dollar trading volume
calculations and existing ranking behavior.

Daily dollar volume is estimated as:

Closing Price * Daily Share Volume

The median is calculated over the existing
twenty-one-session observation window.

Preserve the distinction between screening
qualification, initial result ordering and
report ranking.

#### QPC-11 - Historical trade timing

Preserve historical signal identification,
trade entry timing, exit timing and holding
period calculations.

The existing simulation enters a trade
at the opening price of the next session
following the qualifying signal.

Exit occurs at the closing price of the
final holding session.

The existing integrated default holding
period is five trading sessions.

#### QPC-12 - Transaction costs

Preserve the existing gross and net
trade-return calculations.

Gross Return Percent:

((Exit Price / Entry Price) - 1) * 100

Net Return Percent:

Gross Return Percent - Round Trip Cost Percent

The existing integrated default round-trip
transaction cost is 0.50 percent.

Disclose the simplified nature of this model.

#### QPC-13 - Trade overlap restrictions

Preserve existing same-security trade
overlap restrictions and chronological
signal processing.

Preserve treatment of incomplete trades
and signals that cannot produce a
completed simulation.

Do not convert incomplete trades into
completed losing trades.

#### QPC-14 - Performance statistics

Preserve existing performance calculations,
including:

- Completed trade counts.
- Winning, losing and breakeven trade counts.
- Win rate.
- Average gross return.
- Average net return.
- Average winning and losing returns.
- Expectancy.
- Profit factor.
- Best and worst trade returns.
- Average transaction costs.

Preserve existing behavior for empty samples,
undefined statistics and infinite profit factors.

Individual-trade statistics shall not be
represented as portfolio investment returns.

#### QPC-15 - Signal-date information boundaries

Preserve existing signal-date information
boundaries and calculation-level safeguards
against look-ahead bias.

Future observations shall not influence
earlier historical signal calculations.

Historical regression testing shall use
identical deterministic input data when
comparing application versions.

#### QPC-16 - Research methodology limitations

Clearly disclose the existing limitations:

- Present-day candidate selection bias.
- Absence of a historical point-in-time
  Nasdaq security universe.
- Potentially incomplete corporate-action data.
- Historical market data revisions.
- Indicator warmup history differences.
- Simplified transaction-cost assumptions.
- Absence of portfolio capital allocation modeling.

Historical research results shall not be
represented as guarantees of future performance.

### 4. Regression verification requirements

Version 1.2 and Version 2.0 shall be compared
using identical fixed market observations,
research parameters and relevant source inputs.

Required comparison categories:

- Qualified security sets.
- Screening exclusion behavior.
- Technical indicator calculations.
- Technical scores.
- Missing-value behavior.
- Liquidity measurements.
- Candidate ranking.
- Historical signal dates.
- Trade entry and exit dates.
- Completed and incomplete trade accounting.
- Gross and net trade returns.
- Statistical performance measurements.

Discrete research decisions shall match.

Numerical comparison tolerances shall be
documented and justified before formal
quantitative equivalence acceptance.

### 5. Verification status

Existing baseline evidence:

- Step 6 offline tests: 16 of 16 passed.
- Step 7 offline tests: 18 of 18 passed.
- Total offline tests: 34 of 34 passed.

These results apply to the validated
Version 1.2 source revision.

Version 2.0 quantitative equivalence
has not yet been established.

Implementation and regression verification
remain subject to the approved development
roadmap.

### 6. Change control

All sixteen quantitative preservation
requirements were formally approved on
November 25, 2026.

Any proposed quantitative methodology change
requires explicit user approval, documented
justification and appropriate regression testing.

No methodology change is authorized by
this preservation contract.

The original Version 1.2 application and
both protected archives shall remain unchanged.
