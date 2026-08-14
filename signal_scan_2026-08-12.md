# signal_scan - 2026-08-12

*Generated 2026-08-12 15:42 from `logs\signals_2026-08-12.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-12  (era A-S1D1-B1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +2.41%  raw  44 op  44 damp  0   material adverse move: no
  GM   trail5d   +0.26%  raw  62 op  62 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  1 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at -0.836
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  NKE      -3.21   33   33     0    33     33      33 HIGH   32,32,33,33,33            +1
  AAPL     -3.15   47   47     0    47     47      47 MEDIUM 50,50,55,48,48            -2
  RTX      -1.38   68   68     0    68     68      68 HIGH   65,65,65,70,70            +5
  PM       -1.29   58   58     0    58     58      58 HIGH   57,57,58,58,58            +1
  MSFT     -0.92   70   70     0    70     70      70 HIGH   70,70,72,72,72            +2
  NTR      -0.37   42   42     0    42     42      42 HIGH   43,42,40,40,41            -2
  GM       +0.26   62   62     0    62     62      62 HIGH   63,63,63,63,62            -1
  SPY      +0.50   63   63     0    63     63      63 HIGH   58,60,62,62,62            +4
  VTI      +0.67   63   63     0    63     63      63 HIGH   63,63,63,63,63            +0
  XLU      +0.98   40   40     0    40     40      40 MEDIUM 42,40,40,38,38            -4
  SCHD     +1.11   65   65     0    65     65      65 HIGH   63,63,63,63,65            +2
  CORN     +1.42   43   43     0    43     43      43 MEDIUM 44,43,43,43,42            -2
  QQQ      +1.43   58   58     0    58     58      58 HIGH   54,55,62,58,55            +1
  DOW      +1.53   42   42     0    42     42      42 HIGH   45,45,42,40,42            -3
  PWR      +2.28   63   63     0    63     63      63 HIGH   65,65,65,63,63            -2
  NVDA     +2.37   68   68     0    68     66      66 HIGH   74,72,72,70,68            -6
  WMT      +2.41   44   44     0    44     44      44 HIGH   42,42,42,42,42            +0
  JPM      +2.53   67   67     0    67     67      67 HIGH   67,67,67,67,67            +0
  AIQ      +2.89   58   58     0    58     58      58 HIGH   55,57,58,58,58            +3
  GLD      +4.08   68   68     0    68     59      59 HIGH   62,65,67,68,68            +6
  FTI      +8.93   72   72     0    72     72      72 HIGH   65,65,65,70,72            +7
  SND     +11.65   50   50     0    50     50      50 MEDIUM 40,40,42,42,45            +5
  AG      +12.59   62   62     0    62     62      62 HIGH   58,62,65,62,62            +4
  CBRS    +19.23   42   42     0    42     42      42 MEDIUM 38,38,38,38,42            +4

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [FAIL] D.op == B.blend_op                           22/24
           NVDA   op 68 vs blend_op 66
           GLD    op 68 vs blend_op 59
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
  signals : BUY 2, HOLD 22
  DQ      : HIGH 19, MEDIUM 5
  conf    : mean 56.2  median 60.0  sd(pop) 11.40  min 33  max 72
  at/above the 70% BUY gate: FTI, MSFT
  conf 60-69: 10 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): NVDA, GLD
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 09:32:57 to 09:37:48

Advisory-only - no orders - not financial advice.
```
