#!/usr/bin/env python3
"""
settle_precision.py - settle Check F's PRECISION-tier cells to the log close
(R10, DP-3C-bd). The rule and the writer live in enter_closes.py; this is the
same command under the name the master's How to Use sheet gives it.

    python settle_precision.py            # dry run
    python settle_precision.py --apply    # Excel closed

A cell is settled when it differs from the close the session logs carry by
more than the log's print precision (0.0051) but by less than 0.05%, every log
carrying that session agrees, and settling flips no verdict. Anything else is
left for D9 (an external close) and listed. The evening command
`enter_closes.py --catch-up` runs this too, in the same write.

Advisory-only - no orders - not financial advice.
"""
import sys

import enter_closes

if __name__ == "__main__":
    sys.exit(enter_closes.main(["--settle-precision"] + sys.argv[1:]))
