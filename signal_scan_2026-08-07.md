# signal_scan - 2026-08-07

*Generated 2026-08-07 15:24 from `logs\signals_2026-08-07.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-07  (era A-S1D1-B1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +1.19%  raw  42 op  42 damp  0   material adverse move: no
  GM   trail5d   -1.07%  raw  63 op  63 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  1 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at -0.546
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  CBRS     -3.88   38   38     0    38     38      38 MEDIUM 35,35,38,38,38            +3
  PWR      -2.37   65   65     0    65     65      65 MEDIUM 62,68,65,65,65            +3
  XLU      -1.67   40   40     0    40     40      40 MEDIUM 48,46,44,42,40            -8
  NTR      -1.65   40   40     0    40     40      40 HIGH   50,47,44,43,42            -8
  CORN     -1.25   43   43     0    43     43      43 MEDIUM 47,46,45,44,43            -4
  GM       -1.07   63   63     0    63     63      63 HIGH   65,63,62,63,63            -2
  FTI      -0.82   65   65     0    65     65      65 HIGH   58,62,62,65,65            +7
  NKE      -0.73   33   33     0    33     33      33 MEDIUM 33,33,32,32,32            -1
  DOW      -0.69   42   42     0    42     42      42 HIGH   50,52,48,45,45            -5
  SCHD     +0.67   63   63     0    63     63      63 HIGH   64,63,63,63,63            -1
  PM       +0.80   58   58     0    58     58      58 HIGH   68,65,60,57,57           -11
  JPM      +1.00   67   67     0    67     67      67 HIGH   68,67,68,67,67            -1
  WMT      +1.19   42   42     0    42     42      42 HIGH   45,44,42,42,42            -3
  SPY      +1.92   62   62     0    62     62      62 HIGH   44,48,55,58,60           +16
  VTI      +2.00   63   63     0    63     63      63 HIGH   60,62,62,63,63            +3
  RTX      +2.03   65   65     0    65     65      65 HIGH   65,65,65,65,65            +0
  QQQ      +2.83   62   62     0    62     57      57 HIGH   38,42,48,54,55           +17
  MSFT     +3.38   72   72     0    72     72      72 HIGH   68,72,68,70,70            +2
  AAPL     +3.66   55   55     0    55     55      55 HIGH   52,52,48,50,50            -2
  AIQ      +3.98   58   58     0    58     58      58 HIGH   38,42,52,55,57           +19
  SND      +4.40   42   42     0    42     42      42 MEDIUM 36,42,42,40,40            +4
  GLD      +7.30   67   67     0    67     62      62 HIGH   47,47,47,62,65           +18
  NVDA     +7.98   72   72     0    72     70      70 HIGH   50,68,72,74,72           +22
  AG      +16.08   65   65     0    65     65      65 HIGH   30,42,55,58,62           +32

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [FAIL] D.op == B.blend_op                           21/24
           QQQ    op 62 vs blend_op 57
           NVDA   op 72 vs blend_op 70
           GLD    op 67 vs blend_op 62
  [OK  ] D.op == floor-aware(raw, damp)  [FLOOR=35]   24/24
  [OK  ] HOLD never blend-adjusted (B.blend == B.base) 24/24

  json.confidence_blend semantics (rows where blend != blend_op: n=0):
    UNDETERMINED - no damped rows today, the two values coincide.

------------------------------------------------------------------------------
MATERIAL ADVERSE MOVES TODAY (trail5d <= -5.0%)
------------------------------------------------------------------------------
  none
  Non-tracer rows are context only. The WS2 episode universe is WMT/GM
  by pre-registration; widening it is an amendment, not a reading.

------------------------------------------------------------------------------
COHORT PROFILE
------------------------------------------------------------------------------
  signals : BUY 3, HOLD 21
  DQ      : HIGH 18, MEDIUM 6
  conf    : mean 55.9  median 62.0  sd(pop) 11.95  min 33  max 72
  at/above the 70% BUY gate: MSFT, NVDA
  conf 60-69: 11 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): QQQ, GLD
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 09:33:31 to 09:37:54

Advisory-only - no orders - not financial advice.
```
