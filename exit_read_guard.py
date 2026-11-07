#!/usr/bin/env python3
"""
exit_read_guard.py - the gates every Phase 3-C one-time EXIT READ must pass,
and the one way such a read is recorded.

WHY THIS EXISTS (2026-11-06, DP-3C-bn (i))
    DP-3C-ay: every E4 endpoint is read ONCE, at the exit, together. "Once"
    has to be mechanical. Revised the same day after an independent review
    found three ways the first version could be bypassed or fail silently.

THE GATES (a read is computed only when every one passes)
    0  RUN FROM THE REPO FOLDER. The readings log, the master and the logs are
       resolved from one folder, so a run from elsewhere cannot consult a
       different readings log and read twice.
    1  READ PROTECTION (DP-3C-bb). Every close the read rests on is strictly
       before the master's newest cohort.
    2  INTEGRITY (DP-3C-bm): trading_calendar --selftest, log_tracker_crosscheck
       on the newest log, outcome_sanity (Checks A..I, and Check F must have
       compared at least one cell) and trail_basis_audit, all exit 0, all run
       on the SAME snapshot of the master the read uses.
    3  COMMITTED CODE. Every top-level .py in the folder is tracked, identical
       to HEAD, and flagged neither assume-unchanged nor skip-worktree; no
       untracked or ignored .py sits beside the tools (it could shadow an
       import). Git blob ids are recorded.
    4  NOT ALREADY READ. Read from the readings log STRICTLY: a missing file is
       empty, an unreadable or malformed one STOPS the read.
    5  INPUTS AS RULED. The populations at the cut equal the counts recorded
       in rulings.EXIT_CUT, the logs cover every cohort in the master, and
       no log changes between the start and the end of the run.

RECORDING (record_once)
    All readings of one read are written in ONE atomic write (temp file, then
    os.replace), refused if any is already present, then read back and
    compared. The caller shows nothing until that verification passes.

Advisory-only - no orders - not financial advice.
"""

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- #
# Hashing and the input snapshot
# --------------------------------------------------------------------------- #
def sha256(path):
    """Hex SHA-256 of a file. Raises on an unreadable file: a hash that cannot
    be computed must stop a read, never be recorded as None."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def same_folder(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def gate_cwd(cwd=None):
    cwd = cwd or os.getcwd()
    if same_folder(cwd, HERE):
        return True, f"running in the repo folder {HERE}"
    return False, f"run from the repo folder {HERE}, not {os.path.abspath(cwd)}"


def snapshot(tracker, log_paths, workdir):
    """Copy the master once into `workdir`; hash it and every log. The read and
    every gate then use the copy, so the recorded hash is of the bytes read."""
    dst = os.path.join(workdir, "claude_equity_bot_tracker.xlsx")
    shutil.copyfile(tracker, dst)
    return dict(master=dst, master_sha=sha256(dst), master_src=os.path.abspath(tracker),
                logs={os.path.abspath(p): sha256(p) for p in log_paths})


def logs_unchanged(snap):
    bad = [p for p, h in snap["logs"].items() if not os.path.exists(p) or sha256(p) != h]
    return (not bad), ("logs unchanged since the start of the run" if not bad
                       else "logs changed during the run: " + ", ".join(os.path.basename(p) for p in bad))


# --------------------------------------------------------------------------- #
# The readings log, strictly
# --------------------------------------------------------------------------- #
def load_readings_strict(path):
    """{} when the file does not exist; the parsed dict otherwise. Raises when
    it exists but cannot be read or parsed (rulings._load fails OPEN, which is
    right for streaks and wrong for a one-time read)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("readings log is not a JSON object")
    return data


def _norm(x):
    return json.loads(json.dumps(x, default=str, sort_keys=True))


def record_once(entries, path, now=None):
    """entries: {instrument: (date, passed, detail)}. One atomic write; refused
    if the log is unreadable or any instrument is already recorded; verified by
    reading back. Returns (ok, message)."""
    try:
        data = load_readings_strict(path)
    except (OSError, ValueError) as exc:
        return False, f"readings log unreadable ({exc}); nothing recorded"
    have = [i for i in entries if data.get(i)]
    if have:
        return False, "already recorded: " + ", ".join(have) + "; nothing recorded"
    stamp = (now or dt.datetime.now()).isoformat(timespec="seconds")
    want = {}
    for inst, (date, passed, detail) in entries.items():
        d = dict(detail or {})
        d.setdefault("source", os.path.basename(sys.argv[0]) or "interactive")
        d.setdefault("recorded_at", stamp)
        want[inst] = [{"date": str(date), "pass": bool(passed), "detail": _norm(d)}]
    new = dict(data)
    new.update(want)
    folder = os.path.dirname(os.path.abspath(path))
    tmp = None
    try:
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".readings_", suffix=".json", dir=folder)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(new, f, indent=2, sort_keys=True, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        tmp = None
    except OSError as exc:
        return False, f"write failed ({exc}); nothing recorded"
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    try:
        back = load_readings_strict(path)
    except (OSError, ValueError) as exc:
        return False, f"read-back failed ({exc})"
    bad = [i for i in want if _norm(back.get(i)) != _norm(want[i])]
    kept = [k for k in data if _norm(back.get(k)) != _norm(data[k])]
    if bad or kept:
        return False, f"read-back mismatch: {bad + kept}"
    return True, "recorded and verified: " + ", ".join(want)


def record_exit(entries, exit_path, shared_path):
    """The one way an exit read is recorded: first into the AUTHORITATIVE exit
    readings file (written by nothing else, so no nightly writer can erase it),
    then mirrored into the shared readings log for display. Returns (ok, msg);
    ok follows the authoritative write alone."""
    ok, msg = record_once(entries, exit_path)
    if not ok:
        return False, msg
    ok2, msg2 = record_once(entries, shared_path)
    return True, msg + ("" if ok2 else f"; MIRROR into the shared log not written ({msg2}) - the "
                        "authoritative record stands")


def load_exit_records(instruments, paths):
    """{instrument: first entry} found in any of `paths`, read strictly (raises
    if a file exists but cannot be read)."""
    out = {}
    for p in paths:
        data = load_readings_strict(p)
        for i in instruments:
            if data.get(i) and i not in out:
                out[i] = data[i]
    return out


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #
def gate_read_protection(resolution_sessions, as_of):
    import rulings
    ok, last = rulings.read_protection(list(resolution_sessions), as_of)
    if ok:
        return True, f"every resolving close predates the newest cohort ({last} < {as_of})"
    if last is None:
        return False, "nothing to read (no resolution sessions) or no newest cohort"
    return False, f"the {last} close has not been log-verified (newest cohort {as_of})"


def _run(cmd, cwd, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout or "", p.stderr or ""
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)


_FINDING = re.compile(r"\[(F|C|A|B|G|H|I|FAIL)\]|FINDING|STOP|REGRESSION|MISMATCH|ERROR", re.I)
_INFO = re.compile(r"comparisons made|SUPPRESSED|RESULT: CLEAN|\[OK", re.I)
_F_COUNT = re.compile(r"\[F\] log-close comparisons made: (\d+)")


def gate_integrity(master, logs_glob, newest_log, cwd=HERE, runner=None):
    """DP-3C-bm: the outcome gate. `runner` is injectable for the selftest."""
    run = runner or (lambda cmd: _run(cmd, cwd))
    py = sys.executable
    steps = [
        ("trading_calendar", [py, os.path.join(cwd, "trading_calendar.py"), "--selftest", "--tracker", master]),
        ("log_tracker_crosscheck", [py, os.path.join(cwd, "log_tracker_crosscheck.py"), "--log", newest_log,
                                    "--tracker", master]),
        ("outcome_sanity", [py, os.path.join(cwd, "outcome_sanity.py"), "--tracker", master, "--logs", logs_glob]),
        ("trail_basis_audit", [py, os.path.join(cwd, "trail_basis_audit.py"), "--tracker", master,
                               "--logs", logs_glob, "--quiet"]),
    ]
    bad, notes = [], []
    for name, cmd in steps:
        rc, out, err = run(cmd)
        if name == "outcome_sanity":
            m = _F_COUNT.search(out)
            n = int(m.group(1)) if m else 0
            notes.append(f"Check F compared {n} cell(s)")
            if rc == 0 and n == 0:
                bad.append("outcome_sanity: Check F compared nothing (no logs found?)")
                continue
        if rc != 0:
            lines = [ln.strip() for ln in (out + "\n" + err).splitlines()
                     if _FINDING.search(ln) and not _INFO.search(ln)][:6]
            bad.append(f"{name} exit {rc}: " + (" | ".join(lines) or "see its output"))
    if bad:
        return False, "; ".join(bad)
    return True, "calendar, cross-check, outcome_sanity, trail audit all exit 0 (" + "; ".join(notes) + ")"


def _git(args, cwd):
    rc, out, err = _run(["git"] + list(args), cwd, timeout=120)
    return rc, out.strip(), err.strip()


def git_head(cwd=HERE):
    rc, out, _ = _git(["rev-parse", "HEAD"], cwd)
    return out if rc == 0 else None


def gate_git_strict(required, cwd=HERE):
    """Gate 3. Returns (ok, detail, {file: blob id at HEAD})."""
    rc, _, err = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    if rc != 0:
        return False, f"not a git work tree or git unavailable ({err or rc})", {}
    on_disk = sorted(f for f in os.listdir(cwd) if f.endswith(".py") and os.path.isfile(os.path.join(cwd, f)))
    missing = [f for f in required if f not in on_disk]
    if missing:
        return False, "required file(s) missing: " + ", ".join(missing), {}
    rc, out, err = _git(["ls-files", "-v"], cwd)
    if rc != 0:
        return False, f"git ls-files failed ({err})", {}
    flags = {}
    for ln in out.splitlines():
        if len(ln) > 2 and ln[1] == " ":
            flags[ln[2:]] = ln[0]
    bad = []
    for f in on_disk:
        tag = flags.get(f)
        if tag is None:
            bad.append(f"{f}: not tracked (an untracked .py beside the tools can shadow an import)")
        elif tag == "S":
            bad.append(f"{f}: skip-worktree is set")
        elif tag.islower():
            bad.append(f"{f}: assume-unchanged is set")
    # Anything else at the top level that Python would import ahead of the
    # standard library: compiled modules, and regular packages (__init__ present).
    import importlib.machinery as _m
    for f in sorted(os.listdir(cwd)):
        full = os.path.join(cwd, f)
        if os.path.isfile(full) and any(f.endswith(sfx) for sfx in _m.all_suffixes()) and not f.endswith(".py"):
            bad.append(f"{f}: a compiled module beside the tools (could shadow an import)")
        elif os.path.isdir(full) and f != "__pycache__" and any(
                os.path.exists(os.path.join(full, "__init__" + sfx)) for sfx in _m.all_suffixes()):
            rc2, out2, _ = _git(["status", "--porcelain", "--ignored", "--untracked-files=all", "--", f], cwd)
            if rc2 != 0 or out2:
                bad.append(f"{f}/: a package with untracked, ignored or modified files (could shadow an import)")
    if bad:
        return False, "; ".join(bad), {}
    rc, out, _ = _git(["diff", "--name-only", "HEAD", "--"] + on_disk, cwd)
    if rc != 0:
        return False, "git diff failed", {}
    if out:
        return False, "differs from HEAD: " + ", ".join(out.split()), {}
    blobs = {}
    for f in required:
        rc, out, _ = _git(["rev-parse", f"HEAD:./{f}"], cwd)
        if rc != 0:
            return False, f"no blob at HEAD for {f}", {}
        blobs[f] = out
    head = git_head(cwd) or "?"
    return True, f"{len(on_disk)} top-level .py tracked, clean and unflagged at HEAD {head[:12]}", blobs


def gate_not_recorded(instruments, paths):
    """Gate 4 over every file an exit reading can live in (strict)."""
    paths = [paths] if isinstance(paths, str) else list(paths)
    try:
        have = load_exit_records(instruments, paths)
    except (OSError, ValueError) as exc:
        return False, f"a readings file is unreadable ({exc}): stop, do not read"
    if have:
        return False, "already recorded: " + ", ".join(f"{i} on {e[0].get('date')}" for i, e in have.items())
    return True, "no exit reading on the record for " + ", ".join(instruments)


def gate_inputs(expected, got, extra_ok=True, extra_detail=""):
    keys = set(expected) | set(got)
    diff = {k: (expected.get(k), got.get(k)) for k in sorted(keys) if got.get(k) != expected.get(k)}
    if diff or not extra_ok:
        parts = [f"{k}: ruled {a}, found {b}" for k, (a, b) in diff.items()]
        if not extra_ok:
            parts.append(extra_detail)
        return False, "inputs differ from the ruled cut: " + "; ".join(parts)
    return True, "populations equal the counts ruled in rulings.EXIT_CUT" + (f"; {extra_detail}" if extra_detail else "")


def all_ok(results):
    return all(ok for _, ok, _ in results)


def gate_lines(results):
    return [f"  [{'OK  ' if ok else 'STOP'}] gate {name}: {detail}" for name, ok, detail in results]


# --------------------------------------------------------------------------- #
def selftest():
    sys.path.insert(0, HERE)
    import rulings
    fails = []

    def check(name, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")
        if not ok:
            fails.append(name)

    d = dt.date
    check("protection passes when every session predates as_of",
          gate_read_protection([d(2026, 11, 4), d(2026, 11, 5)], d(2026, 11, 6))[0], True)
    check("protection FAILS when a session equals as_of", gate_read_protection([d(2026, 11, 6)], d(2026, 11, 6))[0], False)
    check("protection FAILS on an empty list", gate_read_protection([], d(2026, 11, 6))[0], False)
    check("cwd gate passes in the tool folder", gate_cwd(HERE)[0], True)
    check("cwd gate FAILS elsewhere", gate_cwd(tempfile.gettempdir())[0], False)

    tmp = tempfile.mkdtemp(prefix="erg_")
    try:
        # --- readings log: strict load, atomic record, verify, refuse twice
        rp = os.path.join(tmp, "logs", "instrument_readings.json")
        check("not-recorded passes when the log does not exist", gate_not_recorded(["X@exit"], rp)[0], True)
        os.makedirs(os.path.dirname(rp))
        rulings.record_reading("H4", d(2026, 11, 6), True, {"v": 0}, path=rp)
        ok, msg = record_once({"X@exit": (d(2026, 11, 7), True, {"v": 1}),
                               "Y@exit": (d(2026, 11, 7), False, {"v": 2})}, rp)
        check("record_once writes both readings and verifies", ok, True)
        back = load_readings_strict(rp)
        check("...and keeps every other instrument's history", back["H4"][0]["detail"]["v"], 0)
        check("rulings.readings sees the new record", rulings.readings("X@exit", path=rp)[0]["detail"]["v"], 1)
        ok, msg = record_once({"X@exit": (d(2026, 11, 7), True, {"v": 9})}, rp)
        check("record_once REFUSES a second record", ok, False)
        check("...and the first stands", load_readings_strict(rp)["X@exit"][0]["detail"]["v"], 1)
        check("not-recorded FAILS once a reading exists", gate_not_recorded(["X@exit"], rp)[0], False)
        with open(rp, "w") as f:
            f.write("{ corrupt")
        check("a corrupt readings log STOPS gate 4 (fails closed)", gate_not_recorded(["Z@exit"], rp)[0], False)
        check("a corrupt readings log STOPS record_once", record_once({"Z@exit": (d(2026, 11, 7), True, {})}, rp)[0], False)
        check("...and is left as it was (nothing overwritten)", open(rp).read(), "{ corrupt")

        # --- the authoritative exit file survives a nightly erase of the shared log
        ep, sp = os.path.join(tmp, "logs", "exit.json"), os.path.join(tmp, "logs", "shared.json")
        ok, msg = record_exit({"W@exit": (d(2026, 11, 7), True, {"v": 1})}, ep, sp)
        check("record_exit writes the authoritative file and the mirror",
              (ok, bool(load_readings_strict(ep).get("W@exit")), bool(load_readings_strict(sp).get("W@exit"))),
              (True, True, True))
        with open(sp, "w") as f:
            f.write("{}")
        check("gate 4 still stops after the shared log loses the record",
              gate_not_recorded(["W@exit"], [ep, sp])[0], False)
        check("gate 4 FAILS closed on an unreadable second file",
              gate_not_recorded(["V@exit"], [ep, os.path.join(tmp, "logs", "instrument_readings.json")])[0], False)
        check("inputs gate FAILS on an unexpected extra key", gate_inputs({"a": 1}, {"a": 1, "b": 2})[0], False)

        # --- integrity gate with an injected runner
        def runner_for(rc_map, fcount=12):
            def run(cmd):
                name = os.path.basename(cmd[1]).replace(".py", "")
                out = f"[F] log-close comparisons made: {fcount} cell(s)\n" if name == "outcome_sanity" else ""
                return rc_map.get(name, 0), out + ("[F] AAPL disagrees\n" if rc_map.get(name) else ""), ""
            return run
        check("integrity passes when all four exit 0", gate_integrity("m", "g", "l", runner=runner_for({}))[0], True)
        check("integrity FAILS when outcome_sanity exits 1",
              gate_integrity("m", "g", "l", runner=runner_for({"outcome_sanity": 1}))[0], False)
        check("integrity FAILS when the cross-check exits 1",
              gate_integrity("m", "g", "l", runner=runner_for({"log_tracker_crosscheck": 1}))[0], False)
        check("integrity FAILS when Check F compared nothing",
              gate_integrity("m", "g", "l", runner=runner_for({}, fcount=0))[0], False)

        # --- git gate
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True)
        if g("init", "-q").returncode == 0:
            g("config", "user.email", "t@t")
            g("config", "user.name", "t")
            for n in ("a.py", "b.py"):
                with open(os.path.join(repo, n), "w") as f:
                    f.write("x = 1\n")
            g("add", "a.py", "b.py")
            g("-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "-m", "a")
            ok, det, blobs = gate_git_strict(["a.py"], cwd=repo)
            check("git gate passes on a clean repo and returns blob ids", (ok, sorted(blobs)), (True, ["a.py"]))
            with open(os.path.join(repo, "b.py"), "a") as f:
                f.write("y = 2\n")
            check("git gate FAILS when ANY top-level .py is modified", gate_git_strict(["a.py"], cwd=repo)[0], False)
            g("checkout", "-q", "--", "b.py")
            with open(os.path.join(repo, "a.py"), "a") as f:
                f.write("y = 2\n")
            g("update-index", "--assume-unchanged", "a.py")
            check("git gate FAILS on assume-unchanged", gate_git_strict(["a.py"], cwd=repo)[0], False)
            g("update-index", "--no-assume-unchanged", "a.py")
            g("update-index", "--skip-worktree", "a.py")
            check("git gate FAILS on skip-worktree", gate_git_strict(["a.py"], cwd=repo)[0], False)
            g("update-index", "--no-skip-worktree", "a.py")
            g("checkout", "-q", "--", "a.py")
            with open(os.path.join(repo, "statistics.py"), "w") as f:
                f.write("# shadow\n")
            check("git gate FAILS on an untracked .py that could shadow an import",
                  gate_git_strict(["a.py"], cwd=repo)[0], False)
            os.remove(os.path.join(repo, "statistics.py"))
            os.makedirs(os.path.join(repo, "json"))
            with open(os.path.join(repo, "json", "__init__.py"), "w") as f:
                f.write("# shadow\n")
            check("git gate FAILS on an untracked package that could shadow an import",
                  gate_git_strict(["a.py"], cwd=repo)[0], False)
            shutil.rmtree(os.path.join(repo, "json"))
            with open(os.path.join(repo, "random.pyc"), "wb") as f:
                f.write(b"\x00")
            check("git gate FAILS on a sourceless .pyc beside the tools", gate_git_strict(["a.py"], cwd=repo)[0], False)
            os.remove(os.path.join(repo, "random.pyc"))
            check("git gate passes again once the shadows are gone", gate_git_strict(["a.py"], cwd=repo)[0], True)
            check("git gate FAILS when a required file is missing", gate_git_strict(["zz.py"], cwd=repo)[0], False)
        else:
            print("  [SKIP] git unavailable: git-gate cases not run")
        nogit = tempfile.mkdtemp(prefix="erg_nogit_")
        check("git gate FAILS outside a work tree", gate_git_strict([], cwd=nogit)[0], False)
        shutil.rmtree(nogit, ignore_errors=True)

        # --- inputs and snapshot
        check("inputs gate passes on equal counts", gate_inputs({"a": 1}, {"a": 1})[0], True)
        check("inputs gate FAILS on any difference", gate_inputs({"a": 1}, {"a": 2})[0], False)
        lp = os.path.join(tmp, "signals_2026-11-06.log")
        mp = os.path.join(tmp, "m.xlsx")
        for p in (lp, mp):
            with open(p, "w") as f:
                f.write("x")
        wd = os.path.join(tmp, "snap")
        os.makedirs(wd)
        snap = snapshot(mp, [lp], wd)
        check("snapshot hashes the copy it will read", snap["master_sha"], sha256(mp))
        check("logs unchanged right after the snapshot", logs_unchanged(snap)[0], True)
        with open(lp, "a") as f:
            f.write("y")
        check("a log changed during the run is caught", logs_unchanged(snap)[0], False)
        try:
            sha256(os.path.join(tmp, "absent"))
            check("an unreadable file raises, never hashes to None", False, True)
        except OSError:
            check("an unreadable file raises, never hashes to None", True, True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("exit_read_guard selftest: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
    return 0 if not fails else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
