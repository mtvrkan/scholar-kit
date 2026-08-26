#!/usr/bin/env python3
"""env_capture.py — the environment a run happened in, as a record rather than a memory.

WHY THIS EXISTS
"scikit-learn 1.5" in a methods section is written months after the run, from
memory, and is wrong roughly as often as it is right — a minor version changed a
default, someone upgraded mid-project, the numbers in the table came from two
different environments nobody noticed. Reproducibility sections are full of this
class of error, and none of it is dishonest: it is just unrecorded.

This captures what is actually loaded — Python, platform, and the installed
version of every package that matters to the run — as a JSON object that
`experiment_db.py` stores in the run record's `env` field, and a short hash that
makes two runs comparable at a glance.

WHAT IT REFUSES
- **To guess what mattered.** With no `--packages`, it records the distributions
  actually importable in this interpreter that appear in a default scientific set;
  with `--all` it records everything installed. It never invents a version for a
  package it cannot find — a missing package is reported as missing, which is
  itself a finding when the run is supposed to have used it.
- **To identify you.** No username, no hostname, no working directory, no
  environment variables. Those would travel with every attestation and none of
  them is part of an experiment's identity. Platform is recorded at the level a
  reader needs (`Windows-10-10.0.19045`, `Linux-6.8.0-x86_64`), not the machine.
- **To name a model it did not count.** `--model` reports the model identities
  found in this project's Claude Code transcripts WITH their turn counts. No
  transcripts, or none carrying a model id, is recorded as `unavailable` with
  the directory that was searched — never as a plausible model name.

WHY --model EXISTS
An AI-use disclosure must name the software and its version, and `compliance_gen.py`
makes `--tool` and `--uses` mandatory — while the kit recorded nothing that could
supply the version. The field the disclosure most needs to be auditable was the
one a run could not produce, so it got filled from session logs outside the kit,
where a reader of the repository cannot check it. `--model` closes that: the
version becomes something the run counted rather than something its author
remembered.

USAGE
  python scripts/env_capture.py                       # the default scientific set
  python scripts/env_capture.py --packages torch,timm # exactly these
  python scripts/env_capture.py --all                 # everything installed
  python scripts/env_capture.py --model --project .   # + which model produced the work

Exit codes: 0 ok · 1 error · 2 a package named with --packages is not installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import emit

# The packages whose version plausibly changes a number in a results table. Not
# a dependency list and not a recommendation — a lookup of what to record IF it
# is installed, so the common case needs no flags.
DEFAULT_PACKAGES = (
    "numpy", "scipy", "pandas", "scikit-learn", "statsmodels", "matplotlib",
    "seaborn", "torch", "torchvision", "torchaudio", "tensorflow", "keras",
    "jax", "xgboost", "lightgbm", "catboost", "transformers", "datasets",
    "tokenizers", "accelerate", "sentence-transformers", "opencv-python",
    "pillow", "nltk", "spacy", "gensim", "librosa", "pywavelets", "shap", "lime",
    "imbalanced-learn", "optuna", "pytorch-lightning",
)


def installed_versions(names) -> tuple[dict, list]:
    found, missing = {}, []
    for name in names:
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
    return dict(sorted(found.items())), missing


def all_installed() -> dict:
    out = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            out[name] = dist.version
    return dict(sorted(out.items()))


def producing_models(project_root: Path) -> dict:
    """Which model(s) actually produced this project's work, counted.

    An AI-use disclosure has to name the software AND its version, and venues
    increasingly require it. The kit made that mandatory in `compliance_gen.py`
    (`--tool` and `--uses` are required) while recording nothing that could
    supply the version: this function captured Python, the platform and the
    package versions, and not the model that did the work. So the one field the
    disclosure most needs to be auditable was the one the run could not produce,
    and a real manuscript ended up filling it from session logs OUTSIDE the kit —
    which the reader of the repository cannot verify.

    Counted, never guessed. Every assistant turn in this project's Claude Code
    transcripts carries a `model`; this reports the distinct identities with
    their turn counts. If the transcripts are not there, that is recorded as
    "unavailable" with the directory that was looked in — an unfound model is
    not an absent one, and neither is a licence to write a plausible id.
    """
    out = {"source": "claude-code-transcripts"}
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from token_report import default_transcript_dir
        d = default_transcript_dir(project_root)
    except Exception as e:                              # pragma: no cover
        return {**out, "status": "unavailable", "reason": f"cannot locate: {e}"}
    out["transcript_dir"] = str(d)
    if not d.is_dir():
        return {**out, "status": "unavailable",
                "reason": "no transcript directory for this project path"}

    counts: dict[str, int] = {}
    files = 0
    for p in sorted(d.glob("*.jsonl")):
        files += 1
        try:
            with p.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"model"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue           # a live transcript can end mid-line
                    m = (rec.get("message") or {}).get("model")
                    # `<synthetic>` marks a harness-generated turn, not model
                    # output; counting it would name a model that never ran.
                    if m and not str(m).startswith("<"):
                        counts[m] = counts.get(m, 0) + 1
        except OSError:
            continue
    if not counts:
        return {**out, "status": "unavailable", "files": files,
                "reason": "transcripts found but no assistant turn carried a model id"}
    return {**out, "status": "counted", "files": files,
            "turns": sum(counts.values()),
            "models": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "note": ("orchestrating sessions only. Subagents run in their own "
                     "transcripts and may sit on a different tier by their "
                     "agent definition; this does not claim otherwise.")}


def capture(packages=None, everything: bool = False, model_root: Path | None = None) -> tuple[dict, list]:
    if everything:
        pkgs, missing = all_installed(), []
    else:
        pkgs, missing = installed_versions(packages or DEFAULT_PACKAGES)
        if not packages:
            missing = []  # absence from the default set is not a finding
    env = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        # platform(), not node(): the OS and architecture are part of a result's
        # identity (a BLAS difference moves the last digits); the machine's name
        # is not, and it identifies a person.
        "platform": platform.platform(terse=True),
        "machine": platform.machine(),
        "packages": pkgs,
    }
    env["hash"] = hashlib.sha256(
        json.dumps(env, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    if model_root is not None:
        # Added AFTER the hash on purpose: the hash exists so two runs can be
        # compared by environment, and a later session appending turns to the
        # transcripts would otherwise change the fingerprint of an environment
        # that did not move.
        env["produced_by"] = producing_models(model_root)
    return env, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--packages", help="comma-separated distribution names to record")
    ap.add_argument("--all", action="store_true", help="record every installed distribution")
    ap.add_argument("--model", action="store_true",
                    help="also record WHICH MODEL produced this project's work, "
                         "counted from the Claude Code transcripts rather than named")
    ap.add_argument("--project", default=".",
                    help="project root, used to locate those transcripts (default: .)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    names = [n.strip() for n in args.packages.split(",") if n.strip()] if args.packages else None
    env, missing = capture(names, args.all,
                           Path(args.project) if args.model else None)
    payload = {"env": env}
    if missing:
        payload["missing"] = missing
        payload["note"] = ("named but not installed — recorded as missing rather "
                           "than given a version, because a run that needed them "
                           "did not happen in this interpreter")
    emit(payload, args.json_out)
    sys.exit(2 if missing else 0)


if __name__ == "__main__":
    main()
