# YÖK Turkish Thesis Requirements

## 1. Front-Matter Order (Mandatory)

Turkish theses require this exact sequence before Chapter 1:

1. **Iç Kapak (Inner Cover)**
   - Title (centered, bold, uppercase)
   - Author name
   - Date, degree level, university
   - Advisor name
   - No page number on this page

2. **Onay Sayfası (Approval Page)**
   - "Dokuz Eylül Üniversitesi Fen Bilimleri Enstitüsü" (or your institution)
   - Degree and program name
   - Student name and ID
   - Thesis title
   - Advisor + committee members (3–5) with titles
   - Approval date, committee signatures
   - Numbered page i (Roman numerals continue through preliminaries)

3. **Etik Beyan (Ethics Declaration)**
   - Standard statement: "Bu tezde [name] tarafından yapılan [tez/çalışma] ... etik kurul tarafından onaylanmıştır / [araştırmanın niteliği gereği etik kurul onayı gerekmemiştir]."
   - If human subjects: ethics approval number and date
   - Student and advisor signature

4. **Teşekkür (Acknowledgments)** — Optional but common
   - 1–2 paragraphs
   - Thank advisors, committee, colleagues, family
   - Formal academic tone

5. **Özet (Turkish Summary)**
   - Length: 250–500 words (check institute guideline)
   - Must mirror Abstract structure exactly (see Section 2)
   - Paragraph breaks, RQ statement, method, findings, implications — in same order as Abstract
   - Keywords: 4–6 in Turkish
   - Page numbered (e.g., v)

6. **Abstract (English Summary)**
   - Same length and structure as Özet
   - Keywords: 4–6 in English (same concepts as Turkish keywords)
   - Page numbered (e.g., vi)

7. **İçindekiler (Table of Contents)**
   - Lists all chapters, sections, subsections (typically 3 levels max)
   - Includes Özet, Abstract, Bibliography, Appendices page numbers
   - Page numbered (e.g., vii)

8. **Tablo Listesi (List of Tables)** — If thesis has ≥3 tables
   - Format: "Table 1. [Caption]  . . . . page X"
   - Page numbered

9. **Şekil Listesi (List of Figures)** — If thesis has ≥3 figures
   - Format: "Figure 1. [Caption]  . . . . page X"
   - Page numbered

10. **Sembol ve Kısaltmalar Listesi (List of Symbols/Abbreviations)** — If needed
    - Alphabetical or by first use
    - Format: "CNNs: Convolutional Neural Networks"

**Page numbering:** Roman numerals (i, ii, iii…) for all preliminary pages from Approval Page onward. Switch to Arabic numerals (1, 2, 3…) starting Chapter 1.

---

## 2. Özet ↔ Abstract Structural Equivalence Rule

**CRITICAL:** The Turkish and English summaries are not free translations. They must be **structurally identical:**

### Mandatory parallel structure:
```
Özet (Turkish)                          Abstract (English)
────────────────                        ─────────────────
¶1: Background & RQ                     ¶1: Background & RQ
¶2: Method                              ¶2: Method
¶3: Results (key finding)               ¶3: Results (key finding)
¶4: Implications & conclusion           ¶4: Implications & conclusion

Keywords: [TR terms]                    Keywords: [EN terms]
```

### Example (imaging study):

**Özet:**
```
Bu tez [background]. Araştırma sorusu [RQ in Turkish]. Yöntem: [method description, sample size, tools].
Sonuçlar: [main finding with numbers]. [Implications]. Anahtar Kelimeler: görüntü işleme, makine öğrenmesi, ...
```

**Abstract:**
```
This thesis [same background]. Research question: [RQ in English]. Method: [same description, N=..., tools].
Results: [identical finding with same numbers]. [Same implications]. Keywords: image processing, machine learning, ...
```

### Checklist before finalization:
- [ ] Both Özet and Abstract have ≥3 paragraphs
- [ ] Paragraph count is identical (n paragraphs each)
- [ ] Claim about sample size (e.g., "N=120") appears in same paragraph in both
- [ ] Key results (metrics, percentages) are numerically identical
- [ ] Keywords are concept-equivalent (not word-for-word translation, but same research topics)
- [ ] Tense and mood match: "X was found" (past) in both languages, not "X is found" vs "X was found"

---

## 3. Turkish Academic Register

### Passive voice norm
Turkish academic writing uses passive voice or impersonal constructions more frequently than English:

| English | Turkish (preferred) |
|---------|---------------------|
| We studied X | X araştırılmıştır / X incelenmiştir |
| The results showed | Sonuçlar göstermiştir |
| We collected data | Veriler toplanmıştır |
| This is important | Bu önemli olduğu görülmektedir |

**NOT:** "Biz araştırdık X" (overly direct; acceptable but less formal).

### Term unity (Terminolojik tutarlılık)
Choose ONE Turkish term per English concept and use it consistently throughout:

| English term | Turkish choice | STICK WITH IT |
|---|---|---|
| deep learning | derin öğrenme | NOT: derin kurma öğrenmesi, kalın ağ, ... |
| transfer learning | aktarım öğrenmesi | NOT: transfer etme, aktarma öğrenmesi |
| overfitting | aşırı uyum | NOT: fazla uyum, uyum sapması |
| ablation study | ablasyon çalışması | (or: öge kaldırma çalışması, but pick one) |

**First mention rule:** Introduce English term in parentheses on first use:
```
"Çalışmamız derin öğrenme (deep learning) tekniklerini kullanmıştır."
```

### TDK number and unit conventions
- Numbers 0–9: spelled out (sıfır, bir, iki…) or digits (0, 1, 2…) — be consistent
- Numbers ≥10: digits only (12, 345, 7.2)
- Units: use international standard abbreviations (mm, kg, s, Hz) — no Turkish suffixes
- Percentage: "% 45" (space after percent) in formal Turkish, OR "%45" — check institution style
- Comma as decimal separator: "2,5 mm" (European style common in TR) vs "2.5 mm" (US, also used in Turkish tech). Check guideline.

---

## 4. Institute Guideline Ingestion

Your institution provides a **thesis guideline PDF or DOCX** with specific requirements (font, margins, spacing, citation style for bibliography, degree-level differences).

### Steps to register it:
1. Save the guideline as `templates/institution/guideline.pdf` (or .docx)
2. Extract key rules and save as `templates/institution/GUIDELINE-NOTES.md`:

```markdown
# [University Name] Thesis Guideline

## Summary of rules:
- Font: Times New Roman 12 pt (body), 14 pt (headings)
- Margins: 2.5 cm (top/bottom/left), 2.0 cm (right)
- Line spacing: 1.5 for body, 1.0 for quotes > 3 lines
- Paragraph spacing: 12 pt before/after sections
- Bibliography style: APA 7 (for social sciences) / IEEE (for engineering)
- Özet & Abstract: max 500 words each
- Figures/tables: captions in Turkish below figure, English below table (or vice versa)
- Front-matter: iç kapak → onay sayfası → etik beyan → teşekkür → Özet → Abstract → İçindekiler → Tablo/Şekil Listesi

## Special notes:
- Ethics approval number MUST appear on Etik Beyan
- Advisor name appears as "[Ünvanı] [Adı]" (e.g., "Doç.Dr. Ahmet Kaya")
- Committee members: minimum 3, max 5
```

3. This skill will then **treat GUIDELINE-NOTES.md as authoritative:** any conflict between the kit's defaults and the guideline, the guideline wins.

---

## 5. Viva Preparation (Turkish-specific notes)

### Committee likely to ask:

**Turkish-context questions:**
- "Türkiye'de bu çalışma nasıl uygulanabilir?" (How would this apply in Turkey's context?)
- "YÖK standartlarına göre [requirement] nasıl sağlanıyor?" (How does this meet YÖK standards for [requirement]?)
- "Türkçe kaynaklar arasında benzeri çalışma var mı?" (Are there similar Turkish-language studies?)

**Advice:**
- Prepare an answer for why TR sources were or were not relevant (bilingual-search skill has rationale logging).
- If your thesis is bilingual (Turkish + English chapters), clarify that decision: "Chapter 1 is in Turkish because [institute requirement / clarity]; Methods in English to align with international practice."
- Practice the Özet↔Abstract mapping explanation: "The Abstract is not a translation, but a structural parallel to ensure equivalence of claims and evidence."

---

## References
- YÖK Tez Yazım Kuralları: tez.yok.gov.tr (search "yazım kuralları")
- Your institution's guideline (ingest via steps in Section 4)
- Turkish academic writing: ../../academic-writing/reference/turkish-academic.md
