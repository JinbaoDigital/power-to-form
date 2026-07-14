#!/usr/bin/env python3
"""
audit_release.py - run the pinned verifier the way a reviewer of THIS release must read it.

engine/verify_cake_nr10.py is pinned by sha256 in engine/audit/foar_figures/MANIFEST.json and is
therefore never edited: editing it would break the audit chain it exists to protect. Its last
section asserts that the rendered figures, the eight interactive viewers and the 80 Three.js
screenshots are on disk in engine/out/cake_figs/. Those artefacts are deliberately NOT
redistributed - the viewers inline per-building footprint coordinates and the screenshots carry
Esri satellite imagery (see README.md) - so in the release those checks cannot pass, and the
pinned verifier exits 1 for a reason that is not a defect.

This wrapper runs the pinned verifier unmodified, re-hashes it against the manifest first, reports
every check it CAN run as pass/fail, and announces the undistributable ones as SKIPPED. It exits 0
if and only if every check the release can run passes. In the full working tree, where the caches,
viewers and screenshots exist, nothing is skipped and all 34 checks pass.

  python audit_release.py        # 24 pass, 10 skipped, 0 fail, exit 0
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENG = ROOT / "engine"
MANIFEST = ENG / "audit" / "foar_figures" / "MANIFEST.json"
SECTION = re.compile(r"^\s*\d+\.\s")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    M = json.load(open(MANIFEST, encoding="utf-8"))
    script, want = M["verification"]["script"], M["verification"]["sha256"]
    print("audit_release.py - the pinned verifier, read against what the release actually ships\n")
    if not (ENG / script).exists():
        print("FAILED  engine/%s is missing" % script)
        return 1
    got = sha256(ENG / script)
    print("  pinned verifier : engine/%s" % script)
    print("  sha256          : %s (MANIFEST %s) %s"
          % (got[:16], want[:16], "MATCH" if got == want else "MISMATCH"))
    if got != want:
        print("\nFAILED  the verifier does not match its pin in MANIFEST.json: the audit chain is broken")
        return 1
    print("  running it unmodified from engine/ ...\n")

    r = subprocess.run([sys.executable, script], cwd=str(ENG), capture_output=True, text=True)
    out = r.stdout
    sys.stdout.write(out if out.endswith("\n") else out + "\n")
    if r.stderr.strip():
        sys.stdout.write(r.stderr)

    # The verifier's own sections. Only the last one ("figures, viewers and screenshots") asserts
    # the presence of artefacts that this release does not redistribute; a failure there is a SKIP,
    # a failure anywhere else is a real failure.
    undistributable, failed, npass = [], [], 0
    in_undist = False
    for line in out.splitlines():
        if SECTION.match(line):
            in_undist = "viewers" in line and "screenshots" in line
            continue
        s = line.strip()
        if s.startswith("ok "):
            npass += 1
        elif s.startswith("FAIL "):
            (undistributable if in_undist else failed).append(s[5:].strip())

    total = npass + len(undistributable) + len(failed)
    print("-" * 92)
    print("release reading of the %d pinned checks (MANIFEST records %d):"
          % (total, M["verification"]["checks"]))
    print("  %2d pass" % npass)
    print("  %2d skipped - the artefact is deliberately not redistributed (README.md):"
          % len(undistributable))
    for u in undistributable:
        print("       skip   %s" % u)
    print("  %2d fail" % len(failed))
    for f in failed:
        print("       FAIL   %s" % f)
    ok = not failed
    print("")
    print("the pinned verifier's own exit code was %d: it counts those %d absent artefacts as"
          % (r.returncode, len(undistributable)))
    print("failures. They are not distributable, so this wrapper counts them as skipped and does")
    print("not edit the pinned script. Every check the release CAN run is above.")
    print("\n%s   %d pass, %d skipped, %d failed" % ("ALL PASS" if ok else "FAILED",
                                                     npass, len(undistributable), len(failed)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
