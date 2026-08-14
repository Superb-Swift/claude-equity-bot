# signal_scan - 2026-08-06

*Generated 2026-08-06 18:06 from `logs\signals_2026-08-06.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-06  (era A-S1D1-B1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +0.93%  raw  42 op  42 damp  0   material adverse move: no
  GM   trail5d   -0.33%  raw  63 op  63 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  1 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at -0.181
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  NTR      -5.18   42   42     0    42     42      42 MEDIUM 48,50,47,44,43            -5
  FTI      -2.22   65   65     0    65     65      65 HIGH   55,58,62,62,65           +10
  PM       -1.69   57   57     0    57     57      57 HIGH   68,68,65,60,57           -11
  XLU      -1.60   40   40     0    40     40      40 HIGH   50,48,46,44,42            -8
  SND      -0.46   40   40     0    40     40      40 MEDIUM 38,36,42,42,40            +2
  GM       -0.33   63   63     0    63     63      63 HIGH   65,65,63,62,63            -2
  CORN     -0.28   43   43     0    43     43      43 MEDIUM 50,47,46,45,44            -6
  DOW      +0.26   45   45     0    45     45      45 HIGH   48,50,52,48,45            -3
  SCHD     +0.63   63   63     0    63     63      63 HIGH   64,64,63,63,63            -1
  WMT      +0.93   42   42     0    42     42      42 MEDIUM 45,45,44,42,42            -3
  AAPL     +1.18   50   50     0    50     50      50 MEDIUM 60,52,52,48,50           -10
  NKE      +1.52   32   32     0    32     32      32 HIGH   33,33,33,32,32            -1
  JPM      +1.53   67   67     0    67     67      67 HIGH   68,68,67,68,67            -1
  PWR      +2.32   65   65     0    65     65      65 HIGH   62,62,68,65,65            +3
  RTX      +2.68   65   65     0    65     65      65 HIGH   65,65,65,65,65            +0
  SPY      +3.11   60   60     0    60     60      60 HIGH   44,44,48,55,58           +14
  VTI      +3.24   63   63     0    63     63      63 HIGH   60,60,62,62,63            +3
  QQQ      +4.47   55   55     0    55     55      55 HIGH   38,38,42,48,54           +16
  GLD      +5.23   65   65     0    65     63      63 HIGH   48,47,47,47,62           +14
  AIQ      +5.77   57   57     0    57     57      57 HIGH   38,38,42,52,55           +17
  MSFT     +6.99   70   70     0    70     70      70 HIGH   62,68,72,68,70            +8
  NVDA     +8.88   72   72     0    72     71      71 HIGH   50,50,68,72,74           +24
  CBRS     +8.97   38   38     0    38     38      38 MEDIUM 35,35,35,38,38            +3
  AG      +16.33   62   62     0    62     62      62 HIGH   32,30,42,55,58           +26

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [FAIL] D.op == B.blend_op                           22/24
           NVDA   op 72 vs blend_op 71
           GLD    op 65 vs blend_op 63
  [OK  ] D.op == floor-aware(raw, damp)  [FLOOR=35]   24/24
  [OK  ] HOLD never blend-adjusted (B.blend == B.base) 24/24

  json.confidence_blend semantics (rows where blend != blend_op: n=0):
    UNDETERMINED - no damped rows today, the two values coincide.

------------------------------------------------------------------------------
MATERIAL ADVERSE MOVES TODAY (trail5d <= -5.0%)
------------------------------------------------------------------------------
  NTR     -5.18%   raw  42 -> op  42 (damp 0)   tracer: no
  Non-tracer rows are context only. The WS2 episode universe is WMT/GM
  by pre-registration; widening it is an amendment, not a reading.

------------------------------------------------------------------------------
COHORT PROFILE
------------------------------------------------------------------------------
  signals : BUY 2, HOLD 22
  DQ      : HIGH 18, MEDIUM 6
  conf    : mean 55.0  median 58.5  sd(pop) 11.56  min 32  max 72
  at/above the 70% BUY gate: MSFT, NVDA
  conf 60-69: 10 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): GLD
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 10:09:28 to 10:14:02

Advisory-only - no orders - not financial advice.
```
