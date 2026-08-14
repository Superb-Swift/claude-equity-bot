# signal_scan - 2026-08-13

*Generated 2026-08-13 11:19 from `logs\signals_2026-08-13.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-13  (era A-S1D1-B1-E1, 25 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +3.21%  raw  46 op  46 damp  0   material adverse move: no
  GM   trail5d   -0.71%  raw  61 op  61 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  2 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v5_3 section 4)
------------------------------------------------------------------------------
  [FAIL] signal count 25 (expected 24)
  [OK  ] era stamp A-S1D1-B1-E1 - EDGAR live (3-C)
  [OK  ] EDGAR sections on 16/25 row(s); 9 dark: AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at -0.419
  [WARN] S1 cold start (no prior state) on: SPCX
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  AAPL     -2.94   52   52     0    52     52      52 HIGH   50,55,48,48,47            -3
  NKE      -1.95   35   35     0    35     35      35 HIGH   32,33,33,33,33            +1
  RTX      -1.55   65   65     0    65     65      65 HIGH   65,65,70,70,68            +3
  MSFT     -0.85   72   72     0    72     72      72 HIGH   70,72,72,72,70            +0
  GM       -0.71   61   61     0    61     61      61 HIGH   63,63,63,62,62            -1
  CBRS     -0.62   38   38     0    38     38      38 MEDIUM 38,38,38,42,42            +4
  PM       +0.04   60   60     0    60     60      60 HIGH   57,58,58,58,58            +1
  NVDA     +0.41   70   70     0    70     75      75 HIGH   72,72,70,68,68            -4
  SPY      +0.51   63   63     0    63     63      63 HIGH   60,62,62,62,63            +3
  GLD      +0.51   65   65     0    65     61      61 HIGH   65,67,68,68,68            +3
  VTI      +0.58   63   63     0    63     63      63 HIGH   63,63,63,63,63            +0
  XLU      +1.03   42   42     0    42     42      42 HIGH   40,40,38,38,40            +0
  PWR      +1.24   65   65     0    65     65      65 HIGH   65,65,63,63,63            -2
  JPM      +1.27   68   68     0    68     68      68 HIGH   67,67,67,67,67            +0
  QQQ      +1.35   57   57     0    57     57      57 HIGH   55,62,58,55,58            +3
  SCHD     +1.43   65   65     0    65     65      65 HIGH   63,63,63,65,65            +2
  AG       +1.49   60   60     0    60     60      60 MEDIUM 62,65,62,62,62            +0
  AIQ      +1.66   58   58     0    58     58      58 HIGH   57,58,58,58,58            +1
  CORN     +2.04   44   44     0    44     44      44 MEDIUM 43,43,43,42,43            +0
  WMT      +3.21   46   46     0    46     46      46 HIGH   42,42,42,42,44            +2
  DOW      +4.35   42   42     0    42     42      42 MEDIUM 45,42,40,42,42            -3
  NTR      +4.71   47   47     0    47     47      47 HIGH   42,40,40,41,42            +0
  SPCX     +6.16   52   52     0    52     52      52 HIGH   COLD                      --
  FTI      +8.98   72   72     0    72     72      72 HIGH   65,65,70,72,72            +7
  SND     +12.17   55   55     0    55     55      55 MEDIUM 40,42,42,45,50           +10

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      25/25
  [OK  ] json.confidence_raw == D.raw                 25/25
  [OK  ] D.raw == B.base                              25/25
  [FAIL] D.op == B.blend_op                           23/25
           NVDA   op 70 vs blend_op 75
           GLD    op 65 vs blend_op 61
  [OK  ] D.op == floor-aware(raw, damp)  [FLOOR=35]   25/25
  [OK  ] HOLD never blend-adjusted (B.blend == B.base) 25/25

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
  signals : BUY 2, HOLD 23
  DQ      : HIGH 20, MEDIUM 5
  conf    : mean 56.7  median 60.0  sd(pop) 10.66  min 35  max 72
  at/above the 70% BUY gate: FTI, MSFT, NVDA
  conf 60-69: 10 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): GLD
            (a HOLD in that band is not a near-miss BUY - do not pool them)
  run window: 10:16:25 to 10:21:27

Advisory-only - no orders - not financial advice.
```
