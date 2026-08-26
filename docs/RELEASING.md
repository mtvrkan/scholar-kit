# Releasing, and minting the DOI

Everything up to the tag is prepared in the repository. The two steps that
follow require credentials and judgement that live with the author, not with the
tooling — which is why they are written down here rather than automated.

## 1. What is already done for 1.0.0

- `CHANGELOG.md` — `[Unreleased]` items moved under `## 1.0.0 — 2026-08-25`
- `CITATION.cff` — `version: 1.0.0`, `date-released: 2026-08-25`
- `.claude-plugin/plugin.json` and `marketplace.json` — `1.0.0`
- `web/src/data/site.ts` — `version: '1.0.0'`, and `docs/` rebuilt from it
  (`npm --prefix web run build`; a version bumped in the source and not rebuilt
  leaves the live page serving the old one, which two tests catch)

Four tests hold these together: the plugin version must equal `CITATION.cff`'s,
the marketplace version must equal the plugin's, `CITATION.cff`'s version must
equal the newest **released** heading in the CHANGELOG, and the built site must
carry the version its source declares. Bump one and forget another, and the suite
fails rather than shipping a mismatch.

### Why the numbering went backwards

Four cycles shipped before this one and were tagged `v1.0.0` … `v1.3.0`. None of
them was announced: the site did not exist, and the kit had no public audience
to receive them. This is the first release anyone is invited to, so it is 1.0.0
and the four before it are renumbered `0.1.0` … `0.4.0` in the CHANGELOG — every
line, date and entry unchanged, only the number on the heading.

That makes the four existing tags wrong rather than merely old, because `v1.0.0`
now points at a commit that is not 1.0.0. They have to be deleted before this is
tagged:

```bash
git push origin :refs/tags/v1.0.0 :refs/tags/v1.1.0 :refs/tags/v1.2.0 :refs/tags/v1.3.0
git tag -d v1.0.0 v1.1.0 v1.2.0 v1.3.0
```

Check first whether any of them has a **GitHub Release** or a minted **Zenodo
DOI** attached. A tag can be deleted; a DOI cannot, and a release someone has
already cited should be left alone — in which case take the next number forward
instead of reusing 1.0.0.

## 2. Tag and publish the GitHub release

```bash
python -m pytest && python scripts/validate_kit.py && claude plugin validate . --strict
git tag -a v1.0.0 -m "Scholar-Kit 1.0.0"
git push origin main --tags
gh release create v1.0.0 --title "Scholar-Kit 1.0.0" --notes-file <(sed -n '/^## 1.0.0/,/^## 0.4.0/p' CHANGELOG.md)
```

Run the three checks first. A release is the one moment where a red suite becomes
permanent.

## 3. Archive on Zenodo → get the DOI

Zenodo mints the DOI; nothing in this repository can. What the repository *can*
decide is what the archived record says, and it does: `.zenodo.json` is read by
Zenodo's GitHub integration at archive time and becomes the citation other
people copy. Without it the record is credited to a GitHub username rather than
to a person and described by the repository blurb —
`test_zenodo_metadata_agrees_with_the_citation_file` keeps its title, licence,
author and keywords equal to `CITATION.cff`, so the project cannot end up with
two different citations for one piece of software.

It deliberately declares **no `version`** (Zenodo takes that from the git tag; a
second copy here is a second thing to forget) and **no `doi`** (minted, not
written) — both asserted by a test. An ORCID belongs in `creators[0].orcid` and
is worth adding before the first archive; leave it out rather than guessing one,
for the same reason the DOI field is empty.

One-time setup:

1. Sign in at [zenodo.org](https://zenodo.org) with the GitHub account that owns
   the repository.
2. **Account → GitHub**, find `scholar-kit`, and flip the toggle **on**.
3. Publish a GitHub release **after** the toggle is on. Zenodo archives that
   release automatically and issues two DOIs:
   - a **concept DOI** that always resolves to the newest version, and
   - a **version DOI** for `v1.0.0` specifically.

Cite the **concept DOI** in `CITATION.cff`. That is the one a reader should
follow when they want "this software", not one frozen snapshot of it.

> A release published *before* the toggle is switched on is not archived. Zenodo
> only sees releases created after it starts watching, so if the first release
> produced no DOI, publish a fresh one.

## 4. Record the DOI

Add to `CITATION.cff`, replacing the placeholder comment at the bottom:

```yaml
doi: "10.5281/zenodo.XXXXXXX"
identifiers:
  - type: doi
    value: "10.5281/zenodo.XXXXXXX"
    description: "Concept DOI — always resolves to the latest version"
```

Then add the badge to both READMEs:

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

### Why the DOI is not already in the file

`tests/test_governance_docs.py::test_citation_declares_no_unearned_doi` **fails
the build** if `CITATION.cff` carries a top-level `doi`. That test is deliberate,
and it is not an obstacle to work around: a DOI written before an archive exists
is a fabricated identifier — the exact defect class this kit is built to prevent,
appearing in the kit's own metadata.

So the order is fixed: archive first, then paste, then delete that test's guard
clause — no, in fact, **change the test**, so it asserts the DOI resolves to a
real archive rather than asserting there is none. The guard should follow the
truth, not be removed once it becomes inconvenient.

Suggested replacement, once the DOI is real:

```python
def test_citation_doi_is_a_zenodo_concept_doi():
    doi = _cff().get("doi")
    assert doi and doi.startswith("10.5281/zenodo."), (
        "CITATION.cff should carry the Zenodo CONCEPT doi once a release is archived")
```

## Siteyi yayına alma — Publishing the site

The landing page is `docs/index.html`, and `docs/CNAME` already contains
`scholar.mtvrkan.com`. GitHub Pages can serve from a branch folder, so **no
workflow file is involved** — this is entirely a settings-plus-DNS task.

**1. DNS** — at the registrar/DNS host for `mtvrkan.com`, add one record:

| Type | Name | Value |
|---|---|---|
| CNAME | `scholar` | `mtvrkan.github.io` |

A subdomain takes a `CNAME` record. (Only an apex domain like `mtvrkan.com`
would need four `A` records to GitHub's IPs — that is not this case, so ignore
that instruction if you meet it in GitHub's docs.) If the DNS is behind
Cloudflare, set the record to **DNS only** (grey cloud) until the certificate is
issued; proxying before then makes GitHub's validation fail in a way that reads
like a DNS error.

**2. GitHub** — repository **Settings → Pages**:
- Source: **Deploy from a branch**
- Branch: `main`, folder: **`/docs`**
- Custom domain: `scholar.mtvrkan.com` (it should already be filled in from
  `docs/CNAME`), then **Save**
- Wait for the certificate, then tick **Enforce HTTPS**

DNS propagation is usually minutes; the certificate can take up to an hour. Until
it is issued the site answers on `mtvrkan.github.io/scholar-kit/` — that is
normal, not a misconfiguration.

**3. Check**

```bash
curl -sI https://scholar.mtvrkan.com | head -1        # expect: HTTP/2 200
curl -s https://scholar.mtvrkan.com | grep -o "<title>.*</title>"
```

Note that `/docs` also holds `PERFORMANCE.md` and `RELEASING.md`, so Pages will
serve them as raw text at `scholar.mtvrkan.com/PERFORMANCE.md`. Harmless, and
occasionally useful — but they are unlinked from the page, so treat them as
reachable, not published.

**If you would rather not use Pages**, the page is a single self-contained file
with no build step: point Netlify, Vercel or Cloudflare Pages at `docs/` and set
the same custom domain. Nothing in the repository assumes Pages except
`docs/CNAME`, which those hosts ignore.

## 5. After the DOI exists

- [ ] `CITATION.cff` — `doi` + `identifiers`
- [ ] `README.md` and `README.tr.md` — badge
- [ ] `test_citation_declares_no_unearned_doi` → replaced per above
- [ ] `.zenodo.json` — nothing to change: it carries neither the DOI nor the
      version, by design. If you added an ORCID, do it here and in `CITATION.cff`
      in the same commit
