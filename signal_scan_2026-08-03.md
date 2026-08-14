# signal_scan - 2026-08-03

*Generated 2026-08-03 15:21 from `logs\signals_2026-08-03.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-03  (era A-S1D1-B1-E1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   -2.27%  raw  44 op  44 damp  0   material adverse move: no
  GM   trail5d   -1.74%  raw  63 op  63 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  1 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp A-S1D1-B1-E1 - EDGAR live (3-C)
  [OK  ] EDGAR sections on 15/24 row(s); 9 dark: AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at 0.287
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  AAPL    -10.04   52   44     8    52     52      44 HIGH   62,62,62,60,52           -10
  PM       -5.17   65   65     0    65     65      65 HIGH   68,72,72,68,68            +0
  FTI      -4.02   62   62     0    62     62      62 HIGH   65,62,60,55,58            -7
  NTR      -2.95   47   47     0    47     47      47 HIGH   40,42,45,48,50           +10
  XLU      -2.39   46   46     0    46     46      46 HIGH   58,58,55,50,48           -10
  WMT      -2.27   44   44     0    44     44      44 HIGH   42,45,47,45,45            +3
  CORN     -2.07   46   46     0    46     46      46 MEDIUM 48,50,50,50,47            -1
  GM       -1.74   63   63     0    63     63      63 HIGH   68,72,68,65,65            -3
  AG       -1.72   42   42     0    42     42      42 HIGH   45,38,35,32,30           -15
  NKE      -1.60   33   33     0    33     33      33 HIGH   33,33,35,33,33            +0
  RTX      -1.20   65   65     0    65     65      65 HIGH   72,68,68,65,65            -7
  SCHD     -1.14   63   63     0    63     63      63 HIGH   68,68,65,64,64            -4
  JPM      -1.12   67   67     0    67     67      67 HIGH   72,72,70,68,68            -4
  GLD      +0.20   47   47     0    47     47      47 HIGH   50,48,46,48,47            -3
  VTI      +1.82   62   62     0    62     62      62 HIGH   60,60,60,60,60            +0
  SPY      +1.91   48   48     0    48     48      48 HIGH   44,44,44,44,44            +0
  QQQ      +3.18   42   42     0    42     42      42 HIGH   40,38,36,38,38            -2
  NVDA     +4.73   68   68     0    68     70      70 HIGH   55,52,50,50,50            -5
  AIQ      +5.03   42   42     0    42     42      42 HIGH   40,38,36,38,38            -2
  DOW      +5.25   52   52     0    52     52      52 HIGH   40,42,48,48,50           +10
  SND      +5.33   42   42     0    42     42      42 MEDIUM 43,42,40,38,36            -7
  CBRS     +8.41   35   35     0    35     35      35 MEDIUM 28,28,28,35,35            +7
  PWR     +14.70   68   68     0    68     68      68 HIGH   50,44,42,62,62           +12
  MSFT    +23.14   72   72     0    72     72      72 HIGH   48,50,50,62,68           +20

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [FAIL] D.op == B.blend_op                           23/24
           NVDA   op 68 vs blend_op 70
  [OK  ] D.op == floor-aware(raw, damp)  [FLOOR=35]   24/24
  [OK  ] HOLD never blend-adjusted (B.blend == B.base) 24/24

  json.confidence_blend semantics (rows where blend != blend_op: n=1):
    tracks B.blend (pre-damping)  : 0/1
    tracks B.blend_op (post-damp) : 1/1
    NOTE: the field named 'confidence_blend' carries the POST-damping value.
          Reading it as the blend channel before damping is a channel error.

------------------------------------------------------------------------------
MATERIAL ADVERSE MOVES TODAY (trail5d <= -5.0%)
------------------------------------------------------------------------------
  AAPL   -10.04%   raw  52 -> op  44 (damp 8)   tracer: no
  PM      -5.17%   raw  65 -> op  65 (damp 0)   tracer: no
  Non-tracer rows are context only. The WS2 episode universe is WMT/GM
  by pre-registration; widening it is an amendment, not a reading.

------------------------------------------------------------------------------
COHORT PROFILE
------------------------------------------------------------------------------
  signals : BUY 1, HOLD 23
  DQ      : HIGH 21, MEDIUM 3
  conf    : mean 52.7  median 47.5  sd(pop) 11.58  min 33  max 72
  at/above the 70% BUY gate: MSFT
  conf 60-69: 9 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): NVDA
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 09:47:31 to 09:52:44

Advisory-only - no orders - not financial advice.
```
