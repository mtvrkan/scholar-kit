"""Fetching a registered dataset (scripts/dataset_fetch.py).

What the tests pin is the set of refusals, because the convenience is not the
point of this script: it fetches only for a dataset that is registered, only when
the licence has actually been read, and it never unpacks an archive member that
points outside the extraction directory.
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dataset_fetch as df  # noqa: E402


def _register(tmp_path, **fields):
    rec = {"id": "DS-0001", "name": "smoke", "source": "other", "license": "unknown",
           "license_verified": False, "files": [], **fields}
    p = tmp_path / "analysis"
    p.mkdir(parents=True, exist_ok=True)
    (p / "datasets.jsonl").write_text(json.dumps(rec, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    return p / "datasets.jsonl"


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "dataset_fetch.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- the licence gate ----------

def test_an_unread_licence_stops_the_download(tmp_path):
    """The load-bearing refusal: downloading is the moment a licence starts to
    matter, so it is checked before the request, not after the bytes are on disk."""
    _register(tmp_path)
    out = json.loads(_run(tmp_path, "--id", "DS-0001", "--url",
                          "http://127.0.0.1:1/x.csv", "--plan", expect=2).stdout)
    assert out["would_refuse"] and "not permission" in out["would_refuse"][0]


def test_a_recorded_but_unverified_licence_is_still_a_refusal(tmp_path):
    # "the page says CC-BY" and "I read the licence" are different claims.
    _register(tmp_path, license="CC-BY-4.0", license_verified=False)
    out = json.loads(_run(tmp_path, "--id", "DS-0001", "--url",
                          "http://127.0.0.1:1/x.csv", "--plan", expect=2).stdout)
    assert "never verified" in out["would_refuse"][0]


def test_a_verified_licence_clears_the_plan(tmp_path):
    _register(tmp_path, license="CC-BY-4.0", license_verified=True)
    out = json.loads(_run(tmp_path, "--id", "DS-0001", "--url",
                          "http://127.0.0.1:1/x.csv", "--plan").stdout)
    assert out["would_refuse"] == []


def test_an_unregistered_dataset_has_no_download_path(tmp_path):
    _register(tmp_path)
    proc = _run(tmp_path, "--id", "DS-0099", "--url", "http://127.0.0.1:1/x.csv",
                "--plan", expect=1)
    assert "not in" in (proc.stderr + proc.stdout)


def test_a_dataset_page_url_is_not_taken_as_a_file_url(tmp_path):
    """The record's `url` is where a human reads about the data. Guessing that it
    is also the file is how a landing page ends up registered as a dataset."""
    _register(tmp_path, license="CC0-1.0", license_verified=True,
              url="https://example.org/datasets/bearing")
    proc = _run(tmp_path, "--id", "DS-0001", "--plan", expect=1)
    assert "download_urls" in (proc.stderr + proc.stdout)


# ---------- archive safety ----------

def test_an_archive_member_pointing_outside_is_refused(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("ok.csv", "a,b\n1,2\n")
        zf.writestr("../../escaped.txt", "gotcha")
    result = df.extract(archive, tmp_path)
    assert result["extracted"] is False and "outside" in result["reason"]
    assert not (tmp_path.parent / "escaped.txt").exists()


def test_a_normal_archive_extracts(tmp_path):
    archive = tmp_path / "ok.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("data/train.csv", "a,b\n1,2\n")
    result = df.extract(archive, tmp_path)
    assert result["extracted"] is True and result["members"] == 1
    assert (Path(result["into"]) / "data" / "train.csv").is_file()


def test_a_non_archive_is_reported_not_raised(tmp_path):
    plain = tmp_path / "data.csv"
    plain.write_text("a,b\n1,2\n", encoding="utf-8")
    assert df.extract(plain, tmp_path)["extracted"] is False


# ---------- naming ----------

class _Resp:
    def __init__(self, headers):
        self.headers = headers


def test_the_filename_comes_from_the_server_before_the_url():
    resp = _Resp({"Content-Disposition": 'attachment; filename="bearing-v2.csv"'})
    assert df._filename_for("https://x.org/download?id=7", resp) == "bearing-v2.csv"


def test_a_query_string_never_becomes_the_filename():
    assert df._filename_for("https://x.org/files/train.csv?token=abc", _Resp({})) == "train.csv"
    # The path's last segment, never the query: `download?id=7&format=csv` is a
    # legal filename on one platform and an error on another.
    assert df._filename_for("https://x.org/download?id=7", _Resp({})) == "download"
    assert df._filename_for("https://x.org/?id=7", _Resp({})) == "download.bin"
