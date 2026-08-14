# signal_scan - 2026-07-31

*Generated 2026-07-31 18:30 from `logs\signals_2026-07-31.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-07-31  (era A-S1D1-B1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   -0.12%  raw  45 op  45 damp  0   material adverse move: no
  GM   trail5d   +0.72%  raw  65 op  65 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  No integrity or reconciliation findings.

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp ['A-S1D1-B1'] (expected ['A-S1D1-B1'])
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at 0.154
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  AAPL    -10.39   52   44     8    52     52      44 HIGH   60,62,62,62,60            +0
  AG       -7.77   30   30     4    30     30      30 HIGH   50,45,38,35,32           -18
  SND      -7.47   36   35     4    36     36      35 MEDIUM 45,43,42,40,38            -7
  FTI      -5.12   58   58     0    58     58      58 HIGH   65,65,62,60,55           -10
  XLU      -2.45   48   48     0    48     48      48 MEDIUM 58,58,58,55,50            -8
  RTX      -1.95   65   65     0    65     65      65 HIGH   72,72,68,68,65            -7
  NKE      -1.46   33   33     0    33     33      33 MEDIUM 35,33,33,35,33            -2
  CORN     -1.45   47   47     0    47     47      47 MEDIUM 54,48,50,50,50            -4
  PM       -1.29   68   68     0    68     68      68 HIGH   62,68,72,72,68            +6
  GLD      -1.15   47   47     0    47     47      47 MEDIUM 52,50,48,46,48            -4
  JPM      -0.78   68   68     0    68     68      68 HIGH   70,72,72,70,68            -2
  NVDA     -0.37   50   50     0    50     50      50 HIGH   63,55,52,50,50           -13
  SCHD     -0.34   64   64     0    64     64      64 HIGH   68,68,68,65,64            -4
  WMT      -0.12   45   45     0    45     45      45 HIGH   38,42,45,47,45            +7
  QQQ      -0.04   38   38     0    38     38      38 HIGH   41,40,38,36,38            -3
  VTI      +0.07   60   60     0    60     60      60 HIGH   60,60,60,60,60            +0
  SPY      +0.16   44   44     0    44     44      44 HIGH   44,44,44,44,44            +0
  AIQ      +0.22   38   38     0    38     38      38 HIGH   42,40,38,36,38            -4
  GM       +0.72   65   65     0    65     65      65 HIGH   65,68,72,68,65            +0
  NTR      +3.21   50   50     0    50     50      50 HIGH   40,40,42,45,48            +8
  DOW      +4.16   50   50     0    50     50      50 HIGH   42,40,42,48,48            +6
  CBRS     +6.22   35   35     0    35     35      35 MEDIUM 32,28,28,28,35            +3
  PWR      +7.35   62   62     0    62     62      62 HIGH   50,50,44,42,62           +12
  MSFT    +17.70   68   68     0    68     68      68 HIGH   46,48,50,50,62           +16

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [OK  ] D.op == B.blend_op                           24/24
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
  AAPL   -10.39%   raw  52 -> op  44 (damp 8)   tracer: no
  AG      -7.77%   raw  30 -> op  30 (damp 4)   tracer: no
  SND     -7.47%   raw  36 -> op  35 (damp 4)   tracer: no
  FTI     -5.12%   raw  58 -> op  58 (damp 0)   tracer: no
  Non-tracer rows are context only. The WS2 episode universe is WMT/GM
  by pre-registration; widening it is an amendment, not a reading.

------------------------------------------------------------------------------
COHORT PROFILE
------------------------------------------------------------------------------
  signals : HOLD 24
  DQ      : HIGH 18, MEDIUM 6
  conf    : mean 50.5  median 49.0  sd(pop) 12.02  min 30  max 68
  at/above the 70% BUY gate: none
  conf 60-69: 8 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): none
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 10:30:50 to 10:35:20

Advisory-only - no orders - not financial advice.
```
