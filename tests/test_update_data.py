"""Tests for scripts/update_data.py's Scopus source-list discovery + conversion."""
import json
import sys

import pytest

sys.path.insert(0, "scripts")
import lib_common  # noqa: E402
import update_data  # noqa: E402


def test_emits_json_summary_on_stdout(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    def boom(*_a, **_k):
        raise RuntimeError("network down")

    monkeypatch.setattr(update_data, "fetch", boom)
    monkeypatch.setattr(update_data, "fetch_scopus", boom)
    monkeypatch.setattr(sys, "argv", ["update_data.py", "--dir", "data"])

    with pytest.raises(SystemExit) as exc:
        update_data.main()
    assert exc.value.code == 1

    summary = json.loads(capsys.readouterr().out)
    assert summary["failures"] == 3
    assert all(v.startswith("fail:") for v in summary["results"].values())
    assert set(summary["results"]) == {"scimago", "doaj", "scopus"}

PAGE_HTML = '''<html><a href="//downloads.ctfassets.net/x/y/z/ext_list_May_2026.xlsx">Sources</a>
<a href="//downloads.ctfassets.net/x/y/w/Scopus_Books_list_February.xlsx">Books</a></html>'''


class FakeResp:
    def __init__(self, text="", content=b"", status=200):
        self.text, self.content, self.status_code = text, content, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_discovers_sources_link_not_books(monkeypatch):
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        if "elsevier.com" in url:
            return FakeResp(text=PAGE_HTML)
        return FakeResp(content=b"fake-xlsx-bytes")

    monkeypatch.setattr(update_data.requests, "get", fake_get)
    monkeypatch.setattr(update_data, "load_workbook_stub", None, raising=False)

    # Patch openpyxl.load_workbook used inside fetch_scopus via monkeypatching the
    # module attribute after import — build a minimal fake workbook.
    class FakeCell:
        def __init__(self, v):
            self.value = v

    class FakeWs:
        def __init__(self, rows):
            self._rows = rows

        def iter_rows(self, values_only=True):
            for r in self._rows:
                yield r

    class FakeWb:
        def __init__(self):
            self.sheetnames = ["Scopus Sources May 2026"]
            self._ws = FakeWs([
                ("Sourcerecord ID", "Source Title", "ISSN", "EISSN", "Active or Inactive"),
                (1, "Active Journal", "11112222", "33334444", "Active"),
                (2, "Dead Journal", "55556666", "", "Inactive"),
            ])

        def __getitem__(self, key):
            return self._ws

        def close(self):
            pass

    import openpyxl
    monkeypatch.setattr(openpyxl, "load_workbook", lambda *a, **k: FakeWb())

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        update_data.fetch_scopus(d, 30)
        out = (d / "scopus.csv").read_text(encoding="utf-8")

    assert "ext_list_May_2026.xlsx" in calls[1]  # Sources link chosen, not Books
    assert "Active Journal,11112222,33334444" in out
    assert "Dead Journal" not in out  # inactive rows filtered


def test_get_retries_on_transient_connection_error_then_succeeds(monkeypatch):
    calls = []

    def flaky_get(url, headers=None, timeout=None):
        calls.append(url)
        if len(calls) < 3:
            raise update_data.requests.ConnectionError("transient")
        return FakeResp(content=b"ok")

    monkeypatch.setattr(update_data.requests, "get", flaky_get)
    monkeypatch.setattr(lib_common.time, "sleep", lambda *_: None)

    r = update_data._get("https://example.org/x", headers={}, timeout=10)
    assert r.content == b"ok"
    assert len(calls) == 3


def test_get_raises_after_exhausting_retries(monkeypatch):
    def always_times_out(url, headers=None, timeout=None):
        raise update_data.requests.Timeout("still down")

    monkeypatch.setattr(update_data.requests, "get", always_times_out)
    monkeypatch.setattr(lib_common.time, "sleep", lambda *_: None)

    with pytest.raises(update_data.requests.Timeout):
        update_data._get("https://example.org/x", headers={}, timeout=10)


def test_missing_link_raises_clear_error(monkeypatch):
    monkeypatch.setattr(update_data.requests, "get",
                        lambda *a, **k: FakeResp(text="<html>no links here</html>"))
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(RuntimeError, match="ext_list"):
            update_data.fetch_scopus(Path(td), 30)


def test_fetch_scopus_failure_partway_through_conversion_preserves_existing_csv(monkeypatch, tmp_path):
    # Regression: writing directly into scopus.csv with a truncating file
    # handle while iterating rows meant an exception PARTWAY through the loop
    # left the destination holding only a header + a few rows, permanently
    # overwriting a previously-complete, good scopus.csv. Simulate exactly
    # that: a row iterator that yields 2 good rows then raises.
    existing = tmp_path / "scopus.csv"
    good_content = "title,issn,eissn\nPreviously Good Journal,99998888,77776666\n"
    existing.write_text(good_content, encoding="utf-8")

    def fake_get(url, headers=None, timeout=None):
        if "elsevier.com" in url:
            return FakeResp(text=PAGE_HTML)
        return FakeResp(content=b"fake-xlsx-bytes")

    monkeypatch.setattr(update_data.requests, "get", fake_get)

    class FakeWs:
        def iter_rows(self, values_only=True):
            yield ("Sourcerecord ID", "Source Title", "ISSN", "EISSN", "Active or Inactive")
            yield (1, "New Active Journal", "11112222", "33334444", "Active")
            raise RuntimeError("simulated mid-conversion failure (corrupt row / process interrupted)")

    class FakeWb:
        def __init__(self):
            self.sheetnames = ["Scopus Sources May 2026"]

        def __getitem__(self, key):
            return FakeWs()

        def close(self):
            pass

    import openpyxl
    monkeypatch.setattr(openpyxl, "load_workbook", lambda *a, **k: FakeWb())

    with pytest.raises(RuntimeError, match="simulated mid-conversion failure"):
        update_data.fetch_scopus(tmp_path, 30)

    # The destination must be untouched — not truncated to a partial header-only file.
    assert existing.read_text(encoding="utf-8") == good_content
    # No leftover .tmp<pid> file from the aborted atomic write.
    assert not list(tmp_path.glob("scopus.csv.tmp*"))
