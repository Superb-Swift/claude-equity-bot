# signal_scan - 2026-08-14

*Generated 2026-08-14 15:18 from `logs\signals_2026-08-14.log`. Advisory-only.*

```
==============================================================================
SIGNAL SCAN - 2026-08-14  (era A-S1D1-B1-E1, 25 rows)
==============================================================================

HEADLINE
  WMT  trail5d   +2.33%  raw  47 op  47 damp  0   material adverse move: no
  GM   trail5d   -1.43%  raw  60 op  60 damp  0   material adverse move: no
  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).
  2 integrity/reconciliation finding(s).

------------------------------------------------------------------------------
RUN INTEGRITY (Daily_Workflow_v6_0 section 4)
------------------------------------------------------------------------------
  [FAIL] signal count 25 (expected 24)
  [OK  ] era stamp A-S1D1-B1-E1 - EDGAR live (3-C)
  [OK  ] EDGAR sections on 16/25 row(s); 9 dark: AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU
  [OK  ] confidence_raw present on all rows
  [OK  ] blend channel present on all rows
  [OK  ] regime_score uniform at -0.484
  [OK  ] S1 prior state present on all rows
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

------------------------------------------------------------------------------
PER-TICKER CHANNELS (sorted by trailing 5-session move)
------------------------------------------------------------------------------
  TKR    trail5d  raw   op  damp  base  blend blend_op DQ     S1 prior chain         dconf
  CBRS     -4.35   40   40     0    40     40      40 MEDIUM 38,38,42,42,38            +0
  NKE      -2.90   35   35     0    35     35      35 HIGH   33,33,33,33,35            +2
  SPCX     -2.00   50   50     0    50     50      50 MEDIUM 52                        +0
  MSFT     -1.44   72   72     0    72     72      72 HIGH   72,72,72,70,72            +0
  GM       -1.43   60   60     0    60     60      60 HIGH   63,63,62,62,61            -2
  RTX      -1.33   65   65     0    65     65      65 HIGH   65,70,70,68,65            +0
  AAPL     -1.10   55   55     0    55     55      55 HIGH   55,48,48,47,52            -3
  GLD      -0.06   62   62     0    62     62      62 HIGH   67,68,68,68,65            -2
  SPY      +0.54   63   63     0    63     63      63 HIGH   62,62,62,63,63            +1
  VTI      +0.68   63   63     0    63     63      63 HIGH   63,63,63,63,63            +0
  SCHD     +0.85   65   65     0    65     65      65 HIGH   63,63,65,65,65            +2
  AIQ      +1.42   58   58     0    58     58      58 MEDIUM 58,58,58,58,58            +0
  QQQ      +1.48   57   57     0    57     57      57 MEDIUM 62,58,55,58,57            -5
  JPM      +1.49   70   70     0    70     70      70 HIGH   67,67,67,67,68            +1
  DOW      +1.59   42   42     0    42     42      42 MEDIUM 42,40,42,42,42            +0
  PM       +1.66   62   62     0    62     62      62 HIGH   58,58,58,58,60            +2
  WMT      +2.33   47   47     0    47     47      47 HIGH   42,42,42,44,46            +4
  XLU      +2.35   44   44     0    44     44      44 HIGH   40,38,38,40,42            +2
  CORN     +2.55   44   44     0    44     44      44 MEDIUM 43,43,42,43,44            +1
  NTR      +3.21   50   50     0    50     50      50 MEDIUM 40,40,41,42,47            +7
  PWR      +3.24   67   67     0    67     67      67 HIGH   65,63,63,63,65            +0
  NVDA     +3.61   72   72     0    72     76      76 HIGH   72,70,68,68,70            -2
  AG       +3.93   60   60     0    60     60      60 MEDIUM 65,62,62,62,60            -5
  FTI      +5.94   72   72     0    72     72      72 HIGH   65,70,72,72,72            +7
  SND     +10.02   58   58     0    58     58      58 MEDIUM 42,42,45,50,55           +13

------------------------------------------------------------------------------
CHANNEL RECONCILIATION
------------------------------------------------------------------------------
  [OK  ] json.confidence == D.op                      25/25
  [OK  ] json.confidence_raw == D.raw                 25/25
  [OK  ] D.raw == B.base                              25/25
  [FAIL] D.op == B.blend_op                           24/25
           NVDA   op 72 vs blend_op 76
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
  signals : BUY 1, HOLD 24
  DQ      : HIGH 16, MEDIUM 9
  conf    : mean 57.3  median 60.0  sd(pop) 10.49  min 35  max 72
  GATE-CLEARING DIRECTIONAL (BUY >= 70%, SELL >= 65%): NVDA BUY 72
            (this is the actionable set - see build_actionable_registry.py)
  HOLD rows at/above 70% (CONTEXT ONLY, not actionable): FTI, JPM, MSFT
  conf 60-69: 9 row(s), of which near-miss BUYs (KEEP-70 population): none
            (a HOLD in that band is not a near-miss BUY - do not pool them;
             nor is a SELL, which clears its own 65% gate)
  run window: 09:32:22 to 09:37:52

Advisory-only - no orders - not financial advice.
```
