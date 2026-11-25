# Vancouver/ICMJE Citation Style

Used in medicine, health sciences, and biomedical publishing. Similar to IEEE: citations are **numbered sequentially** [1], [2], etc., in order of first appearance in text.

## In-Text Citations

| Context | Format | Example |
|---------|--------|---------|
| Single citation | [1] | A study [1] found… or Smith et al. [1] reported… |
| Multiple citations | [1]–[3] or [1],[2],[3] | Multiple studies [1]–[3] demonstrate… |
| Citation with page | [1(p. 45)] | A key finding [1(p. 45)] is… |

Numbers are assigned sequentially; reuse the same number for subsequent citations to the same reference.

## Reference List Format (20+ Source Types)

### Journal Article (print and/or online)
```
1. Smith J, Jones K. Title of article in sentence case. Journal Title. 2023;45(2):234-251.
```

### Journal Article (with DOI)
```
2. Brown L. Article title in sentence case. Research Quarterly. 2022;18(3):445-462. doi: 10.1234/example
```

### Journal Article (online, no DOI)
```
3. Davis RM, Wilson H. Examining the phenomenon. Research Quarterly. 2021;52(1):78-92. Accessed January 15, 2024. www.example.com/article-url
```

### Book
```
4. Smith KA. Title of the book in title case. 3rd ed. Publisher Name; 2020.
```

### Book Chapter
```
5. Jones MR. Chapter title in sentence case. In: Davis L, ed. Edited Book Title in Title Case. Academic Press; 2019. p. 45-67.
```

### Conference Proceeding
```
6. Williams PJ. Paper title in sentence case. In: Proceedings of the 2023 International Conference on Computing; June 15-17, 2023; City, Country. Publisher; 2023. p. 234-241.
```

### Doctoral Dissertation
```
7. Johnson RA. Title of Dissertation in Title Case [dissertation]. University Name; 2022. Accessed via ProQuest Dissertations and Theses.
```

### Master's Thesis
```
8. Lee S. Title of Thesis in Title Case [master's thesis]. University Name; 2021.
```

### Dataset
```
9. National Center for Biotechnology Information. Gene Database: Release 233.0 [dataset]. Published 2023. doi: 10.5281/zenodo.example
```

### Software
```
10. TensorFlow Developers. TensorFlow: An open-source machine learning library [software]. Version 2.12.0. Published 2023. Accessed January 15, 2024. www.tensorflow.org
```

### Preprint
```
11. Taylor N, Kumar A. Attention mechanisms revisited. arXiv. Published 2023. Accessed January 15, 2024. arxiv.org/abs/2301.12345
```

### Webpage
```
12. World Health Organization. COVID-19 guidelines. Published 2023. Accessed January 15, 2024. www.who.int/emergencies/diseases/novel-coronavirus-2019/
```

### Report (Government/Organization)
```
13. U.S. Department of Education. National Education Trends Report. Government Publishing Office; 2023.
```

### Technical Standard
```
14. International Organization for Standardization. ISO/IEC 27001:2022 Information Security Management Systems. 5th ed. ISO; 2020.
```

### Translated Work
```
15. Kühn TS. The Structure of Scientific Revolutions. Translated by Kübra Fidan. 3rd ed. Alpha Publishing House; 2020. Originally published in German as Kuhn TS. Die Struktur wissenschaftlicher Revolutionen. 1962.
```

### Institutional Author
```
16. Turkish Statistical Institute. National Income Report 2022. TÜİK Publications; 2023.
```

### Newspaper Article
```
17. Reporter P. Breaking news headline. The New York Times. March 15, 2023:A1.
```

### Work with No Individual Author
```
18. Turkish Academy of Sciences. Turkish Language Terminology Guide. Published 2023. Accessed January 15, 2024. tdk.gov.tr/
```

### Multiple Authors
```
# One to six authors (list all)
1. Smith J, Jones K, Brown L, Davis R, Wilson H, Taylor N. Article title. Journal. 2023;10:1-10.

# Seven or more authors (list first six et al.)
2. Smith J, Jones K, Brown L, Davis R, Wilson H, Taylor N, et al. Article title. Journal. 2023;10:20-30.
```

### Same Author, Multiple Years
```
1. Smith J. First article. Journal A. 2020;10:1-10.
2. Smith J. Second article. Journal B. 2023;10:20-30.
```

---

## Turkish-Specific Examples

### Turkish Medical Journal Article
```
1. Kaya M, Şimşek G. Görüntü sınıflandırmada derin evrişimsel ağların performansı. Mühendislik Bilimleri ve Tasarım Dergisi. 2023;11(2):245-258. doi: 10.21923/jesd.example
```

### Turkish Thesis
```
2. Özdemir A. Derin öğrenme kullanarak Türkçe metin sınıflandırması [dissertation]. Boğaziçi University; 2021.
```

### Turkish Book
```
3. Çağdaş A, Erbil D. Yönetim Bilimi Temel Kavramlar. 4th ed. Eğitim Yayınları; 2019.
```

### Turkish Institutional Author (Health/Government)
```
4. Ministry of Health, Turkey. 2023 Sağlık Raporu. Government Publishing Office; 2023.
```

---

## Key Formatting Rules

1. **Author names:** List all authors up to six; if seven or more, list first six and add "et al."
   - Format: LastName FI, LastName FI, … (initials only, no periods between initials)

2. **Title case vs sentence case:**
   - Article/chapter titles: sentence case (capitalize only first word, proper nouns, first word after colon)
   - Journal/book titles: Title Case (capitalize major words)

3. **Journal abbreviations:** Use Index Medicus abbreviations (optional but preferred for medical journals)
   - Example: "J Am Med Assoc" instead of "Journal of the American Medical Association"

4. **Dates:** Day Month Year format or Month Year
   - Example: "15 January 2023" or "January 2023"

5. **Page numbers:** Use hyphens for ranges (p. 45-51), not en-dashes

6. **Volume and issue:**
   - Format: volume(issue):pages
   - Example: 2023;45(2):234-251

7. **DOI:** Include if available; format: "doi: 10.1234/example" (no https://)

8. **URLs:** Include full URL for online-only sources

9. **Months:** Full month name or standard abbreviation (Jan, Feb, Mar, etc.)

---

## Common Pitfalls

| Mistake | Fix |
|---------|-----|
| Out-of-order citations | Renumber to match text order. |
| Inconsistent author abbreviation | Use initials only: FI (not First Initial). |
| Missing DOI on recent articles | Check PubMed or CrossRef for DOI. |
| Abbreviating all journal names inconsistently | Use Index Medicus standard abbreviations consistently. |
| Turkish characters lost in romanization | Maintain UTF-8; never convert ç→c, ğ→g, etc. |
| Incomplete book chapter information | Always include page range (p. XX-XX) for chapters. |
| Incorrect et al. threshold | Correct threshold is 7+ authors (not 4+). |
