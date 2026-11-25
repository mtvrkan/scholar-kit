# Turkish Academic Writing Conventions

> **The machine-checkable subset of this document is enforced by
> `scripts/tr_style_check.py`** — decimal-separator consistency, TDK percent
> placement, `vb.`/`vs.`, conversational register, term unity (against the
> per-project glossary `templates/tr-terminology.json`), impersonal/first-person
> voice mixing, and Özet↔Abstract equivalence. Run it before `style-auditor`, not
> instead of it: the script has no parser and no morphology, so everything below
> about agreement, participles and postpositions is still read by a human.
>
> Where this document states a *preference* and the field is genuinely split
> (decimal comma vs point; impersonal vs first-person), the script flags the
> **mixture** and never the choice. Guidance here says what is conventional; the
> checker only says what is inconsistent.

## Passive Voice Norm (Yapılmıştır, Bulunmuştur)

Turkish academic tradition heavily favors passive voice. Unlike English (which prefers active), Turkish readers expect impersonal, passive constructions in formal writing.

### Examples

| Context | Active (Rare) | Passive (Standard) |
|---------|------|--------|
| **Methods** | Araştırmacılar 50 katılımcı işe aldı. | 50 katılımcı araştırmaya **alınmıştır**. (50 participants were recruited into the study) |
| **Results** | Sonuçlar %95 doğruluk gösterdi. | %95 doğruluk **elde edilmiştir**. (95% accuracy was obtained.) |
| **Prior work** | Smith veri analiz etti. | Smith tarafından veriler **analiz edilmiştir**. (Data was analyzed by Smith.) |

### Register Effect

- **Passive:** "Veriler SPSS kullanarak **analiz edilmiştir**" (standard, formal, impersonal).
- **Active:** "Biz SPSS ile veri **analiz ettik**" (less formal, more personal; OK in rare cases like first-person retrospectives).

### Exception: Introduction (Slightly less passive)

Introduction can afford slightly more active voice when stating general truths about the field:

> "Derin öğrenme, görüntü sınıflandırmada **devrim yaratmıştır**." (Deep learning **has revolutionized** image classification.) [passive via perfect tense, but feels less strictly impersonal]

vs. strict passive:

> "Görüntü sınıflandırmada, derin öğrenme tarafından devrim **sağlanmıştır**." (Image classification has **been revolutionized** by deep learning.) [more formal]

---

## Term Unity (Tek Bir Term = Tek Bir Kavram)

**Golden rule:** Once you choose a Turkish term for a concept, use ONLY that term throughout the thesis. Do not alternate between synonyms.

### Setting up a term

On **first mention**, provide both:
1. **Turkish term** (main term you'll use henceforth).
2. **English term in parentheses** (for international readers and clarity).

### Example

> "Yapay sinir ağları (İngilizce: *artificial neural networks*, kısaltma: YSA) çok katmanlı bir mimari üzerine kuruludur. YSA'lar, her katmanda bağlantılar aracılığıyla veri işlerler..."

(Artificial neural networks (English: artificial neural networks, abbreviation: ANN) are built on a multi-layer architecture. ANNs process data through connections in each layer...)

### Common Mistranslations (Unity Issues)

| Concept | Inconsistent Usage | Unified Approach |
|---------|------------------|-----------------|
| "Learning rate" | "Öğrenme oranı," "öğrenme hızı," "hız parametresi" | Pick one: "öğrenme hızı" + (EN: learning rate) |
| "Overfitting" | "Aşırı öğrenme," "eğitim aşırı uyumu" | Pick one: "aşırı öğrenme" (EN: overfitting) |
| "Dataset" | "Veri seti," "veri kümesi," "veri tabanı" | Pick one: "veri seti" (EN: dataset) — note "veri tabanı" = database, different! |
| "Model" | "Model," "ağ," "sistem" | Use "model" consistently (EN: model) |

### Why It Matters

- **Professional appearance:** Shows command of terminology.
- **Clarity:** Readers know "öğrenme hızı" always means "learning rate" (not sometimes "hız parametresi").
- **Translation quality:** If thesis is later translated, unified terms translate consistently.

### TDK (Turkish Language Association) Convention

For numbers and units, follow TDK standards:

| Item | Standard | Wrong |
|------|----------|-------|
| **Decimals** | Comma, not period: "0,95" | "0.95" ❌ |
| **Thousands separator** | Space: "1 000 000" (optional) | "1,000,000" (English style) ❌ |
| **Percent** | Sign BEFORE the number, no space: "%95" | "95%," "95 %" ❌ |
| **Units** | Space before unit: "10 mm," "50 g" | "10mm," "50g" ❌ |
| **Time** | "saat 14:30" (24-hour) | "2:30pm" ❌ |

### Abbreviations

- Define on first use: "Yapay Sinir Ağları (YSA)"
- Use consistently after: "YSA'lar…"
- Plural: Add Turkish suffix "-lar"/"-ler": "YSA'lar" (ANNs), "YYA'lar" (DNNs), not "ANNs".

---

## Common Expression Errors (Turkey-Specific)

### 1. "Elde etmek" vs. "Almak" (Obtaining results)

| Wrong | Right | English |
|-------|-------|---------|
| "Sonuçlar **alınmıştır**" | "Sonuçlar **elde edilmiştir**" | Results were **obtained** (not "taken") |
| "Veriler **alındı**" | "Veriler **toplanmıştır** / **elde edilmiştir**" | Data were **collected** (not "taken") |

**Rule:** "Almak" = take/receive something given; "Elde etmek" = obtain through effort/analysis.

### 2. "Göstermek" vs. "Ortaya koymak" (Show/demonstrate)

| Context | Term | English |
|---------|------|---------|
| "Sonuçlar **göstermiştir**" | Graphs/tables show | Results demonstrate/show |
| "Araştırma **ortaya koymaktadır**" | Research demonstrates (builds/put forward) | Research demonstrates/establishes |

**Rule:** "Göstermek" for direct visualization; "Ortaya koymak" for building an argument.

### 3. "Başarılı" (Successful) — Overused

| Weak | Better |
|------|--------|
| "Yöntem **başarılı**dır" | "Yöntem %95 doğruluk **elde eder**" (achieves 95% accuracy) |
| "Sonuçlar **başarılı** bulunmuştur" | "Sonuçlar **önceki çalışmaları geçmiştir**" (results exceeded prior work) |

**Rule:** Show success via data; don't just declare "başarılı."

### 4. "Çalışma" (Study) vs. "Araştırma" (Research)

| Context | Term | English |
|---------|------|---------|
| "Smith tarafından yapılan **çalışma**" | A specific empirical study | Study |
| "Bu **araştırma**..." (your work) | Broader research endeavor | This research / our research |

**Rule:** "Çalışma" = a discrete study; "araştırma" = broader investigation.

### 5. "İlgili" (Related) — Avoid Overuse

| Weak | Better |
|------|--------|
| "İlgili **çalışmalar** göstermektedir…" | "Prior studies göstermektedir…" or "Smith et al. (2020) bulmuştur…" |
| "İlgili yazında…" | "Literatürde…" or "Bilinen sonuçlar…" |

**Rule:** "İlgili" is vague; name the studies or topic explicitly.

### 6. "Sonuç" (Conclusion) vs. "Sonuç Olarak" (In conclusion)

| Correct Usage |
|---|
| **Sonuç bölümünde** (in the Conclusion section) |
| **Sonuç olarak,** (In conclusion,) — used as transition |
| **Sonuç (isim):** bulunan sonuç / ulaşılan sonuç (noun: finding/conclusion reached) |

**Example:** "Sonuç olarak, bu araştırmanın sonuçları göstermektedir ki…" (In conclusion, this research's findings show that…)

---

## Abstract ↔ Özet Structural Equivalence

Turkish theses require both English Abstract and Turkish Özet. **They must be structurally and substantively equivalent** (not literal translation, but same content + structure).

### Required Sections (Both Languages)

| Section | Turkish (Özet) | English (Abstract) |
|---------|---|---|
| **Problem statement** | Araştırma sorunu | Research problem |
| **Methods** | Yöntem | Methods |
| **Key findings** | Temel bulgular | Main findings |
| **Conclusion / Implications** | Sonuç ve çıkarımlar | Conclusions and implications |
| **Keywords** | Anahtar sözcükler (5–10) | Keywords (same 5–10, English) |

### Check (Before Submission)

- [ ] Özet and Abstract have same structure (intro → methods → findings → conclusion).
- [ ] Both mention the same research question.
- [ ] Both report the same key findings (no surprises).
- [ ] Both have 150–250 words (or per institution spec).
- [ ] Keywords in Turkish = English keywords translated (or English terms if Turkish lacks equivalents).

---

## Sentence-Level Grammar Issues (Common in Turkish-Author Papers)

### 1. Subject-Verb Agreement in Relative Clauses

| Wrong | Right |
|-------|-------|
| "Verileri işlemek için yazılan **programlar başarılı bulunmuş**." | "Verileri işlemek için yazılan **programlar başarılı bulunmuştur**." |

**Rule:** Passive perfect tense: "...bulunmuştur" (singular), "...bulunmuşlardır" (plural).

### 2. Passive Participle Formation

| Wrong | Right | English |
|-------|-------|---------|
| "Analiz eden veriler…" | "Analiz **edilen** veriler…" | Analyzed data |
| "Yayımla yapılan araştırma…" | "Yayımlanmış araştırma…" | Published research |

**Rule:** Past participle for passive voice: "-miş/-muş" or "-en/-an".

### 3. Prepositional Phrases (Postpositions in Turkish)

| Structure | Example |
|-----------|---------|
| Noun + "-de/-da" (in/on) | Araştırmada (in the research) |
| Noun + "-nın/-nin" (of/genitive) | Araştırmanın sonuçları (research's results) |

**Common error:** English word order bleeding into Turkish. Keep postpositions after nouns.

---

## Keyword Best Practices (Turkish + English)

Choose 5–10 keywords that:
1. Appear in your Özet and Abstract.
2. Match your research domain (searchable terms).
3. Reflect your paper type (not too broad; not too narrow).
4. Are consistent between Turkish and English versions.

### Example

**Turkish:** derin öğrenme, yapay sinir ağları, görüntü sınıflandırması, hata teşhisi, titreşim analizi

**English:** deep learning, artificial neural networks, image classification, fault diagnosis, vibration analysis

---

## References & Resources

- **TDK (Turkish Language Association):** tdk.gov.tr — Standard Turkish terminology.
- **YÖK Thesis Guideline:** Consult your institution's thesis submission guideline (most follow YÖK standards).
- **Bilkent/ODTÜ thesis templates:** Often include passive voice examples and proper formatting.
