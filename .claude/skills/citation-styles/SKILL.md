---
name: citation-styles
description: "Master multiple academic citation styles and ensure zero-drift bibliography formatting. Answers QUESTIONS about styles: how to cite a given source type, what a style requires in-text and in the reference list, and what switching between styles does or does not involve (for instance whether the references have to be rewritten — they do not). To actually perform the switch on this project's manuscript, use /restyle instead. Triggers on: 'cite this source', 'citation format', 'APA style', 'MLA style', 'Chicago', 'IEEE', 'Vancouver', 'Harvard', 'bibliography', 'references format', 'do I have to rewrite my references', 'APA'dan IEEE'ye geçmek ne gerektirir'."
---

# Citation Styles — Golden Rules and Multi-Format Reference

The kit enforces **one immutable golden rule:** bibliographic data lives in **one place only** (`bib/references.bib`), fetched machine-wise via `doi2bib.py`. In-text citations use pandoc syntax `[@surname2024key]` everywhere. Style is applied **only at render time** via CSL (Citation Style Language), making journal/format switches instant and error-free.

## Golden Rules (Non-Negotiable)

### 1. BibTeX Is Never Hand-Written

Entries in `bib/references.bib` are populated in exactly two ways:

1. **Via `doi2bib.py`:** given a DOI, fetch authoritative BibTeX from `doi.org` (content negotiation with `Accept: application/x-bibtex`), or fallback to Crossref title search.
   ```bash
   python scripts/doi2bib.py --doi 10.1145/3558535.3559545
   python scripts/doi2bib.py --title-search "Attention is All You Need" --year 2017
   ```
   
2. **Via `bib_doctor.py`:** bulk fix, dedup, and validate existing entries — but never add new fields by hand.

Any entry that cannot be resolved (missing DOI, unpublished preprint, dataset without DOI) is **flagged `verified: false`** and blocked from final output. The workflow is:
- Scout finds a source → registry entry created (status: candidate)
- If source has a DOI, `doi2bib.py` fetches the entry → added to references.bib with `verified: true`
- If no DOI exists, the entry is marked `verified: false` and the agent proposes how to proceed (Crossref title search, manual CrossRef lookup, or exclusion)

### 2. In-Text Citations Are Always Pandoc Syntax

Regardless of style, every in-text citation uses **pandoc's citation syntax:**
```
[@surname2024keyword]           single citation
[@surname2024a; @smith2023]     multiple sources
[@surname2024, p. 45]           with page number (optional)
Page 45 [@surname2024, p. 45]   narrative citation
```

Do **not** write:
- ~~(Author, 2024)~~ — style-specific format; changes per journal
- ~~Author (2024)~~ — same problem
- ~~\cite{key}~~ — LaTeX-only; breaks Markdown+Word workflows

Pandoc automatically converts `[@key]` into the target style at render time. Verify style output before submission with a pandoc one-liner (see Render Test below).

### 3. Journal/Style Switch = One Config Line

When changing target journals:
- **Keep** `bib/references.bib` untouched (machine-fetched, canonical)
- **Change only** PROJECT.md's `- **Citation style:**` bullet — the CSL File
  Mapping table below resolves it to the actual `.csl` file at build time
- Example: `PROJECT.md` has `- **Citation style:** apa7` → change to `ieee` → rebuild → all citations auto-convert

This is the token economy win: zero rewriting of text or bibliography.

## CSL File Mapping

PROJECT.md's `- **Citation style:**` bullet holds an enum key, not a
filename — resolve it against `templates/csl/` via this table before any
`pandoc --csl ...` call:

| PROJECT.md key | CSL file (in `templates/csl/`) |
|---|---|
| `apa7` | `apa.csl` |
| `mla9` | `modern-language-association.csl` |
| `chicago-author-date` | `chicago-author-date.csl` |
| `chicago-notes` | `chicago-notes-bibliography.csl` |
| `ieee` | `ieee.csl` |
| `vancouver` | `vancouver.csl` |
| `harvard` | `harvard-cite-them-right.csl` |
| `csl:<file>` | `<file>` verbatim (user-supplied CSL, e.g. from `/ingest-template`) |

Never guess a filename by lowercasing/reformatting the key (`apa7` is **not**
`apa7.csl` — that file does not exist in this kit).

## Reference Files (by style)

Each style file below explains:
- **In-text patterns:** how to write citations for single/multiple/page/narrative contexts
- **Reference-list formats:** 20+ source types (journal article, book, chapter, conference paper, thesis, dataset, software, preprint, webpage, report, standard, translation, institutional author, no-date, 1/2/3–20/21+ authors, same-author-same-year, secondary citation)
- **Turkish-specific cases:** translated works, institutional authors (e.g., TÜİK, AFAD), Turkish characters in names

| File | Coverage |
|------|----------|
| [apa7.md](reference/apa7.md) | APA 7th Edition (most common in social sciences, psychology, education) |
| [mla9.md](reference/mla9.md) | MLA 9th Edition (humanities, literature, languages) |
| [chicago.md](reference/chicago.md) | Chicago Manual of Style 17th Edition (notes-bibliography and author-date systems) |
| [ieee.md](reference/ieee.md) | IEEE (engineering, computer science, conferences) |
| [vancouver.md](reference/vancouver.md) | Vancouver/ICMJE (medicine, health sciences) |
| [harvard.md](reference/harvard.md) | Harvard (business, social sciences, diverse disciplines) |

## Building Bibliography and Rendering

### Step 1: Populate `bib/references.bib` (via Scripts, Not By Hand)

```bash
# Fetch entry for a DOI
python scripts/doi2bib.py --doi 10.1038/nature12373 --append bib/references.bib

# Verify all entries against authoritative records
python scripts/doi2bib.py --verify --bib bib/references.bib
# Output: 47 refs: 45 PASS, 1 FIX (year mismatch; suggested patch), 1 FABRICATED
```

### Step 2: Write Markdown with Pandoc Citations

```markdown
## Results

Attention mechanisms have become foundational to modern NLP [@vaswani2017attention; 
@devlin2018bert]. A meta-analysis of 200 transformer-based papers [@smith2023transformer] 
found that 87% outperformed RNN baselines, with the largest gains on sequence-to-sequence 
tasks. The original transformer architecture [@vaswani2017attention, p. 3] introduced 
scaled dot-product attention to parallelize computation across input positions.
```

### Step 3: Render to Target Style via Pandoc

```bash
# Render to APA 7
pandoc --from markdown --to docx \
  --bibliography bib/references.bib \
  --citeproc --csl templates/csl/apa.csl \
  --output output.docx \
  draft.md

# Render to IEEE
pandoc --from markdown --to html \
  --bibliography bib/references.bib \
  --citeproc --csl templates/csl/ieee.csl \
  --output output.html \
  draft.md
```

The kit's `docx_build.sh` and `latex_build.sh` scripts wrap this; see the
docx-output and latex-thesis skills.

### Step 4: Verify Citations (Pre-Submission)

```bash
# Cross-check in-text keys vs bibliography
python scripts/cite_audit.py --file draft.md --bib bib/references.bib

# Verify all entries have resolved (not fabricated)
python scripts/doi2bib.py --verify --bib bib/references.bib
```

If any key is undefined or an entry is flagged `FABRICATED`, the build halts and the citation-verifier agent investigates.

## Turkish Source Handling

When citing Turkish academic sources, the challenges are:
1. **No DOI:** Many Turkish journals and all theses from YÖK don't have DOIs. Record provenance instead (thesis number, DergiPark URL, TR Dizin ID).
2. **Author names:** Turkish characters (ç, ğ, ı, ö, ş, ü) must be preserved. BibTeX fields may need special encoding; CSL handles UTF-8 directly.
3. **Institutional authors:** Authors like "Türkiye İstatistik Kurumu" (TÜİK) or "Yazarı Belirtilmemiş" (Anonymous) require special handling.
4. **Translated works:** When citing a work translated from English to Turkish, clarify: is the citation for the English original, the Turkish translation, or both?

### Example: Turkish Thesis (No DOI)

```bibtex
@phdthesis{ozdemir2021deep,
  author = {Özdemir, Ayşe},
  title = {Derin öğrenme kullanarak Türkçe metin sınıflandırması},
  school = {Boğaziçi Üniversitesi},
  year = {2021},
  type = {PhD thesis},
  note = {YÖK Thesis ID: 714382; accessed from \url{https://tez.yok.gov.tr/}},
  keywords = {Turkish, NLP, deep learning},
}
```

In the paper, cite as `[@ozdemir2021deep]`.

### Example: Turkish Journal (TR Dizin)

```bibtex
@article{kaya2023deep,
  author = {Kaya, Mehmet and Şimşek, Gülden},
  title = {Görüntü sınıflandırmada derin evrişimsel ağların performansı},
  journal = {Mühendislik Bilimleri ve Tasarım Dergisi},
  year = {2023},
  volume = {11},
  number = {2},
  pages = {245--258},
  note = {TR Dizin indexed; \url{https://dergipark.org.tr/tr/pub/mbtd/issue/...}},
}
```

In-text: `[@kaya2023deep]` or `Kaya and Şimşek [@kaya2023deep] found that…`

### Example: Translated Work (Original + Translation)

```bibtex
@book{kuhn1996structure,
  author = {Kuhn, Thomas S.},
  title = {The Structure of Scientific Revolutions},
  publisher = {University of Chicago Press},
  year = {1996},
  edition = {3rd},
  note = {Translated to Turkish as: Bilimsel Devrimlerin Yapısı, translated by Kübra Fidan, İstanbul: Alfa Yayınları, 2018.},
}
```

If citing the Turkish translation specifically:

```bibtex
@book{kuhn2018yapisin,
  author = {Kuhn, Thomas S.},
  title = {Bilimsel devrimlerin yapısı},
  translator = {Kübra Fidan},
  publisher = {Alfa Yayınları},
  year = {2018},
  address = {İstanbul},
  note = {Translated from the English original: The Structure of Scientific Revolutions (3rd ed., University of Chicago Press, 1996).},
}
```

## Style Testing

Before final submission, test your bibliography output:

```bash
# Render 5 sample entries in target style (visual check)
echo "Test [@key1; @key2]." | pandoc --citeproc --csl templates/csl/apa.csl --bibliography bib/references.bib -f markdown -t html  # eyeball 2-3 entries in target style
```

This generates an HTML file showing how a sample of 5 random entries renders in the target style. Verify:
- [ ] Author names are formatted correctly (Last, First vs First Last)
- [ ] Titles use proper capitalization (Title Case vs sentence case)
- [ ] URLs appear if the style requires them
- [ ] Page numbers and issue numbers are present
- [ ] Turkish characters display correctly

## Common Pitfalls

| Mistake | Fix |
|---------|-----|
| Manually editing `references.bib` | Use `doi2bib.py --doi` or `bib_doctor.py` to modify entries. Never hand-edit. |
| In-text citations like `(Author, 2024)` | Use `[@key]` pandoc syntax only. The style layer handles formatting. |
| Mixing citation styles in one document | Set `citation_style` in PROJECT.md to one CSL file; all citations auto-format. |
| Adding page numbers in the bib entry | Page numbers go in-text: `[@key, p. 45]`. The reference list should contain only if it's a book chapter with a page range. |
| Turkish names rendered as ASCII | Ensure UTF-8 encoding in .bib file and CSL processing; never romanize (ç → c). |
| Missing DOI for a recent journal article | If Crossref has it, use `doi2bib.py --title-search "title"`. If not, mark `verified: false` and exclude from final output (or manually verify it's valid). |

## See Also

- `doi2bib.py` — execute `python scripts/doi2bib.py --help` to fetch/verify entries.
- `bib_doctor.py` — execute `python scripts/bib_doctor.py --help` to check, dedup, and normalize a bibliography.
- `cite_audit.py` — execute `python scripts/cite_audit.py --file draft.md --bib bib/references.bib` to verify in-text keys (or omit `--file` to audit every file under `--drafts`, default `drafts/`).
- Pandoc documentation: https://pandoc.org/MANUAL.html#citations
- CSL specification: https://citeproc-js.readthedocs.io/
