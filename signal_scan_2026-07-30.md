# signal_scan - 2026-07-30

*Generated 2026-07-30 14:12 from `logs\signals_2026-07-30.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-07-30  (era A-S1D1-B1, 24 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +1.95%  raw  45 op  45 damp  0   material adverse move: no
  GM   trail5d   +5.24%  raw  65 op  65 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  1 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [OK  ] signal count 24 (expected 24)
  [OK  ] era stamp ['A-S1D1-B1'] (expected ['A-S1D1-B1'])
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at -0.061
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  FTI     -10.50   55   47     8    55     55      47 HIGH   68,65,65,62,60            -8
  AG       -9.23   32   32     6    32     32      32 MEDIUM 48,50,45,38,35           -13
  SND      -8.79   38   35     6    38     38      35 LOW    45,45,43,42,40            -5
  NVDA     -5.98   50   49     1    50     50      49 HIGH   62,63,55,52,50           -12
  XLU      -3.58   50   50     0    50     50      50 MEDIUM 55,58,58,58,55            +0
  CORN     -1.78   50   50     0    50     50      50 HIGH   52,54,48,50,50            -2
  JPM      -1.38   68   68     0    68     68      68 HIGH   70,70,72,72,70            +0
  RTX      -1.04   65   65     0    65     65      65 HIGH   72,72,72,68,68            -4
  NKE      -0.92   33   33     0    33     33      33 MEDIUM 35,35,33,33,35            +0
  QQQ      -0.85   38   38     0    38     38      38 HIGH   40,41,40,38,36            -4
  SCHD     -0.53   64   64     0    64     64      64 HIGH   67,68,68,68,65            -2
  SPY      -0.49   44   44     0    44     44      44 HIGH   44,44,44,44,44            +0
  VTI      -0.48   60   60     0    60     60      60 HIGH   60,60,60,60,60            +0
  AAPL     -0.37   60   60     0    60     60      60 HIGH   60,60,62,62,62            +2
  AIQ      -0.26   38   38     0    38     38      38 HIGH   42,42,40,38,36            -6
  DOW      -0.18   48   48     0    48     48      48 HIGH   48,42,40,42,48            +0
  CBRS     +0.04   35   35     0    35     35      35 MEDIUM 35,32,28,28,28            -7
  PM       +0.15   68   68     0    68     68      68 HIGH   63,62,68,72,72            +9
  GLD      +1.08   48   48     0    48     48      48 HIGH   52,52,50,48,46            -6
  PWR      +1.50   62   62     0    62     62      62 HIGH   52,50,50,44,42           -10
  WMT      +1.95   45   45     0    45     45      45 MEDIUM 38,38,42,45,47            +9
  NTR      +2.17   48   48     0    48     48      48 HIGH   38,40,40,42,45            +7
  GM       +5.24   65   65     0    65     65      65 HIGH   62,65,68,72,68            +6
  MSFT    +17.12   62   62     0    62     62      62 HIGH   48,46,48,50,50            +2

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      24/24
  [OK  ] json.confidence_raw == D.raw                 24/24
  [OK  ] D.raw == B.base                              24/24
  [OK  ] D.op == B.blend_op                           24/24
  [FAIL] D.damp == D.raw - D.op                       22/24
           AG     damp 6 but raw-op 0
           SND    damp 6 but raw-op 3
  [OK  ] HOLD never blend-adjusted (B.blend == B.base) 24/24

  json.confidence_blend semantics (rows where blend != blend_op: n=3):
    tracks B.blend (pre-damping)  : 0/3
    tracks B.blend_op (post-damp) : 3/3
    NOTE: the field named 'confidence_blend' carries the POST-damping value.
          Reading it as the blend channel before damping is a channel error.

------------------------------------------------------------------------------
MATERIAL ADVERSE MOVES TODAY (trail5d <= -5.0%)
------------------------------------------------------------------------------
  FTI    -10.50%   raw  55 -> op  47 (damp 8)   tracer: no
  AG      -9.23%   raw  32 -> op  32 (damp 6)   tracer: no
  SND     -8.79%   raw  38 -> op  35 (damp 6)   tracer: no
  NVDA    -5.98%   raw  50 -> op  49 (damp 1)   tracer: no
  Non-tracer rows are context only. The WS2 episode universe is WMT/GM
  by pre-registration; widening it is an amendment, not a reading.

------------------------------------------------------------------------------
COHORT PROFILE
------------------------------------------------------------------------------
  signals : HOLD 24
  DQ      : HIGH 18, LOW 1, MEDIUM 5
  conf    : mean 50.6  median 48.5  sd(pop) 11.56  min 32  max 68
  at/above the 70% BUY gate: none
  conf 60-69: 9 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): none
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 09:57:05 to 10:01:48

Advisory-only - no orders - not financial advice.
```
