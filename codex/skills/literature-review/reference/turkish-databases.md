# Turkish Academic Databases — Coverage, Query Patterns & Provenance

Turkey has three primary academic databases for peer-reviewed and thesis literature. No public APIs exist; access is via web search and URL scraping only.

## TR Dizin (Turkish Citation Index)

**URL:** https://trdizin.gov.tr  
**Coverage:** ~500 Turkish peer-reviewed journals indexed for impact factor and citation metrics; includes engineering, medicine, social sciences, humanities.  
**Audience:** Turkish academics, librarians, higher-education administrators.

### What's Indexed?
- Peer-reviewed Turkish journals (ISSN registered)
- Some bilingual journals (published in TR, abstracts often in EN)
- Not indexed: predatory or non-peer-reviewed Turkish journals
- Not indexed: theses, conference proceedings (see DergiPark & YÖK instead)

### Query Pattern (Site-Scoped WebSearch)

```
site:trdizin.gov.tr [keywords]
site:trdizin.gov.tr "derin öğrenme" "rulman arızası"
site:trdizin.gov.tr anomali tespiti 2023
site:trdizin.gov.tr yazarı:"Mehmet Kaya"
```

Returns: journal name, volume/issue/pages, IF2 (TR Dizin Impact Factor), year, abstract (usually Turkish + some English).

### Metadata Quirks

| Issue | Workaround |
|-------|-----------|
| No DOI on result page | Use title + author + year to cross-check Crossref; many TR Dizin journals also have DOIs |
| Abstract in TR only | Copy to translator (DeepL or Claude) for screening; if unclear, request full text |
| Author order not standardized | Some entries show "Kaya, M.; Şimşek, G." (surname-first); others show "Mehmet Kaya, Gülden Şimşek" |
| ISSN instead of ISBN for books (rare) | Still use ISSN for venue matching in venue_check.py |

### Inclusion in Bibliography

If DOI exists (query Crossref), use DOI in BibTeX entry.  
If no DOI, use `note` field to record provenance:

```bibtex
@article{kaya2023deep,
  author = {Kaya, Mehmet and Şimşek, Gülden},
  title = {Görüntü sınıflandırmada derin evrişimsel ağların performansı},
  journal = {Mühendislik Bilimleri ve Tasarım Dergisi},
  year = {2023},
  volume = {11},
  number = {2},
  pages = {245--258},
  note = {TR Dizin indexed; retrieved from https://trdizin.gov.tr/}
}
```

## DergiPark (Open-Access Turkish Journals)

**URL:** https://dergipark.org.tr  
**Coverage:** ~1,500 open-access Turkish academic journals; growing collection of full-text PDFs.  
**Audience:** Turkish researchers, international readers.

### What's Indexed?
- Peer-reviewed Turkish journals (open-access focus)
- Some hybrid journals (some articles OA, some paywalled)
- Mix of quality: high-quality peer-reviewed journals alongside lower-impact journals
- Theses are NOT here (see YÖK instead)

### Query Pattern (Site-Scoped WebSearch)

```
site:dergipark.org.tr [keywords]
site:dergipark.org.tr "derin öğrenme"
site:dergipark.org.tr CNN titreşim 2023
site:dergipark.org.tr yazar:"Mehmet Kaya"
```

Returns: journal name, article title (in Turkish, sometimes EN abstract), PDF link (often directly accessible).

### Metadata Quirks

| Issue | Workaround |
|-------|-----------|
| Quality highly variable | Check journal IF (in TR Dizin) before including; flag low-quality venues as Strength 1–2 |
| No DOI on many entries | Record DergiPark URL + article ID in `note` field |
| Language inconsistency | Some articles have English titles + Turkish text; some reverse |
| PDF embedded metadata may be poor | Extract bibliographic data via title + author instead of relying on PDF metadata |

### Inclusion in Bibliography

```bibtex
@article{ozer2023transfer,
  author = {Özer, Fatih and Gürel, Deniz},
  title = {Transfer öğrenme ile görüntü sınıflandırması},
  journal = {Bilgisayar Mühendisliği Dergisi},
  year = {2023},
  volume = {10},
  number = {1},
  pages = {45--58},
  note = {DergiPark open-access; URL: https://dergipark.org.tr/tr/pub/bilkom/issue/.../article/...},
  url = {https://dergipark.org.tr/tr/pub/bilkom/...}
}
```

## YÖK Ulusal Tez Merkezi (National Thesis Center)

**URL:** https://tez.yok.gov.tr/UlusalTezMerkezi  
**Coverage:** ~1 million Turkish theses (BSc capstones, MSc theses, PhD dissertations) from all Turkish universities since ~1980s.  
**Audience:** Turkish researchers, international researchers, librarians.

### What's Indexed?
- All accredited Turkish universities' theses (mandatory deposit)
- Full-text PDF access varies: some open, some restricted to Turkish IP / Turkish university logins
- Metadata: always publicly available; full text depends on university/thesis classification

### Query Pattern (Site-Scoped WebSearch)

```
site:tez.yok.gov.tr [keywords]
site:tez.yok.gov.tr "derin öğrenme" rulman
site:tez.yok.gov.tr "anormallik tespiti" 2022 2023
site:tez.yok.gov.tr üniversitesi:"Boğaziçi Üniversitesi"
```

Returns: thesis title, author, university, year, program (MSc/PhD), abstract (Turkish, often English translation too), access status (open/restricted), thesis ID number.

### Metadata Quirks

| Issue | Workaround |
|-------|-----------|
| Full-text access restricted (Turkish IPs only) | Record title + author + year + thesis ID in bibliography; note "restricted access"; try ProQuest or request from author |
| Thesis IDs are unique but not widely known | Always record thesis ID (e.g., "YÖK Thesis ID: 714382") in `note` field for full traceability |
| No DOI assigned | Use thesis ID + URL as permanent identifier |
| English translations of Turkish titles vary in completeness | Prefer Turkish title (authoritative); include English translation in `note` |
| Some old theses have poor metadata (pre-1995 especially) | Extract what's available; note incompleteness |

### Inclusion in Bibliography

```bibtex
@phdthesis{ozdemir2021deep,
  author = {Özdemir, Ayşe},
  title = {Derin öğrenme kullanarak Türkçe metin sınıflandırması},
  school = {Boğaziçi University},
  year = {2021},
  type = {PhD thesis},
  note = {YÖK National Thesis Center, Thesis ID: 714382; access status: open; 
          URL: https://tez.yok.gov.tr/UlusalTezMerkezi/},
  url = {https://tez.yok.gov.tr/UlusalTezMerkezi/}
}
```

For MSc theses:

```bibtex
@mastersthesis{yilmaz2022survey,
  author = {Yılmaz, Mehmet},
  title = {Konvolüsyonel sinir ağları ile anomali tespiti: Bir derleme},
  school = {Istanbul Technical University},
  year = {2022},
  type = {Master's thesis},
  note = {YÖK Thesis ID: 712145; access status: restricted; 
          recorded from YÖK UNTM database},
}
```

---

## Site-Scoped WebSearch Query Tips

When the scout agent runs WebSearch for Turkish sources:

1. **Phrase searching:** Use quotes for exact phrases.
   ```
   site:trdizin.gov.tr "derin öğrenme" "rulman arızası"  ← more specific
   site:trdizin.gov.tr derin öğrenme rulman arızası       ← broader (AND is implicit)
   ```

2. **Year filtering (sometimes works):**
   ```
   site:tez.yok.gov.tr rulman 2022 2023
   site:dergipark.org.tr titreşim 2021..2023             ← date range (database-dependent)
   ```

3. **Author searching (varies):**
   ```
   site:trdizin.gov.tr yazarı:"Kaya, Mehmet"   ← TR Dizin syntax
   site:dergipark.org.tr yazar:"Mehmet Kaya"   ← DergiPark syntax (first name first)
   site:tez.yok.gov.tr "Mehmet Kaya"           ← YÖK (search in full metadata)
   ```

4. **Combining databases:**
   ```
   (site:trdizin.gov.tr OR site:dergipark.org.tr) "derin öğrenme"
   (site:trdizin.gov.tr OR site:dergipark.org.tr OR site:tez.yok.gov.tr) rulman
   ```

---

## Provenance Recording (When No DOI)

For Turkish sources without a DOI, **always record provenance** in the BibTeX `note` field:

```bibtex
note = "TR Dizin indexed; https://trdizin.gov.tr/Pub/Details?id=... [accessed 2024-01-15]"
note = "DergiPark open-access; Article ID: 1234567; https://dergipark.org.tr/tr/pub/journal/... [accessed 2024-01-15]"
note = "YÖK UNTM Thesis ID: 714382; restricted access; https://tez.yok.gov.tr/UlusalTezMerkezi/ [accessed 2024-01-15]"
```

This ensures:
1. **Reproducibility:** another researcher can find the source again (URLs stable for years)
2. **Citation chain:** readers can access the source even if it doesn't have a DOI
3. **Access transparency:** note records if access is restricted (important for readers outside Turkey)

---

## International Registry (Scopus, Web of Science)

Many Turkish journal articles also appear in:
- **Scopus** (www.scopus.com) — broader than Web of Science
- **Web of Science** (via Clarivate; requires institution access) — stricter inclusion criteria

Before deciding a paper is "TR-only", check:
```
scout → doi2bib.py --title-search "Turkish Paper Title" → cross-check Scopus & Crossref
```

Turkish papers published in high-quality journals often have DOIs and appear in Scopus/WoS. Only if Scopus + Crossref return nothing should you mark as "TR-only."

---

## Quality Tiers (Turkish Venues)

| Tier | Examples | Inclusion? |
|------|----------|-----------|
| **Tier 1 (High)** | TR Dizin journals with IF >1, also in Scopus/SCI-E | Always include |
| **Tier 2 (Medium)** | TR Dizin indexed, IF <1 or no IF yet, peer-reviewed | Include; note lower impact |
| **Tier 3 (Lower)** | DergiPark journals, no TR Dizin listing, peer-review unclear | Assess rigorously; document decision |
| **Tier 4 (Grey)** | Theses (inherently high quality if from top universities, but not peer-reviewed in journal sense) | Include with caveats; note "unpublished thesis" |

Always mark **venue quality in registry:** use `venue_check.py --title` to populate `venue_meta.tr_dizin: true|false`.
