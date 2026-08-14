# signal_scan - 2026-08-05

*Generated 2026-08-05 15:28 from `logs\signals_2026-08-05.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-05  (era A-S1D1-B1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +1.30%  raw  42 op  42 damp  0   material adverse move: no
  GM   trail5d   +0.48%  raw  63 op  63 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  1 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at 0.009
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  AAPL     -6.69   50   47     3    50     50      47 HIGH   62,60,52,52,48           -14
  NTR      -5.50   43   42     1    43     43      42 MEDIUM 45,48,50,47,44            -1
  PM       -3.36   57   57     0    57     57      57 HIGH   72,68,68,65,60           -12
  XLU      -3.00   42   42     0    42     42      42 HIGH   55,50,48,46,44           -11
  DOW      -2.49   45   45     0    45     45      45 HIGH   48,48,50,52,48            +0
  NKE      -1.54   32   32     0    32     32      32 HIGH   35,33,33,33,32            -3
  CORN     -0.96   44   44     0    44     44      44 MEDIUM 50,50,47,46,45            -5
  GM       +0.48   63   63     0    63     63      63 HIGH   68,65,65,63,62            -6
  SCHD     +0.64   63   63     0    63     63      63 HIGH   65,64,64,63,63            -2
  FTI      +1.11   65   65     0    65     65      65 HIGH   60,55,58,62,62            +2
  WMT      +1.30   42   42     0    42     42      42 MEDIUM 47,45,45,44,42            -5
  RTX      +2.52   65   65     0    65     65      65 MEDIUM 68,65,65,65,65            -3
  JPM      +2.82   67   67     0    67     67      67 HIGH   70,68,68,67,68            -2
  SND      +2.88   40   40     0    40     40      40 MEDIUM 40,38,36,42,42            +2
  GLD      +3.23   62   62     0    62     62      62 MEDIUM 46,48,47,47,47            +1
  PWR      +3.93   65   65     0    65     65      65 HIGH   42,62,62,68,65           +23
  VTI      +4.18   63   63     0    63     63      63 MEDIUM 60,60,60,62,62            +2
  SPY      +4.25   58   58     0    58     58      58 HIGH   44,44,44,48,55           +11
  QQQ      +5.76   54   54     0    54     54      54 HIGH   36,38,38,42,48           +12
  CBRS     +6.47   38   38     0    38     38      38 MEDIUM 28,35,35,35,38           +10
  AIQ      +7.00   55   55     0    55     55      55 HIGH   36,38,38,42,52           +16
  MSFT     +8.84   70   70     0    70     70      70 HIGH   50,62,68,72,68           +18
  NVDA    +12.43   74   74     0    74     75      75 HIGH   50,50,50,68,72           +22
  AG      +12.52   58   58     0    58     58      58 HIGH   35,32,30,42,55           +20

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [FAIL] D.op == B.blend_op                           23/24
           NVDA   op 74 vs blend_op 75
  [OK  ] D.op == floor-aware(raw, damp)  [FLOOR=35]   24/24
  [OK  ] HOLD never blend-adjusted (B.blend == B.base) 24/24

  json.confidence_blend semantics (rows where blend != blend_op: n=2):
    tracks B.blend (pre-damping)  : 0/2
    tracks B.blend_op (post-damp) : 2/2
    NOTE: the field named 'confidence_blend' carries the POST-damping value.
          Reading it as the blend channel before damping is a channel error.

------------------------------------------------------------------------------
MATERIAL ADVERSE MOVES TODAY (trail5d <= -5.0%)
------------------------------------------------------------------------------
  AAPL    -6.69%   raw  50 -> op  47 (damp 3)   tracer: no
  NTR     -5.50%   raw  43 -> op  42 (damp 1)   tracer: no
  Non-tracer rows are context only. The WS2 episode universe is WMT/GM
  by pre-registration; widening it is an amendment, not a reading.

------------------------------------------------------------------------------
COHORT PROFILE
------------------------------------------------------------------------------
  signals : BUY 2, HOLD 22
  DQ      : HIGH 16, MEDIUM 8
  conf    : mean 54.6  median 57.5  sd(pop) 11.41  min 32  max 74
  at/above the 70% BUY gate: MSFT, NVDA
  conf 60-69: 8 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): GLD
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 09:53:21 to 09:58:18

Advisory-only - no orders - not financial advice.
```
