---
name: analyze-data
description: "Dispatch data-scientist to analyze your data or reproduce analysis. The agent runs Python (pandas, numpy, scipy, matplotlib, scikit-learn), produces figures/tables with reproducible scripts, and registers results as evidence cards. Gate: PROJECT.md complete."
disable-model-invocation: true
argument-hint: "<path|task>"
---

# Analyze Your Data

This skill runs analysis on your data: exploratory statistics, model training/evaluation, figure production. All outputs are reproducible scripts + publication-ready figures/tables + evidence cards.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim.

## GATE: PROJECT.md Complete

**Check:** Read PROJECT.md. Verify NO TBD values in these fields:
- topic ✓
- rqs ✓
- type ✓
- output_language ✓

**If any field is TBD:**
```
❌ PROJECT.md tamamlanmamış. Eksik alan(lar):
  - [field1]
  - [field2]

Lütfen /new-project çalıştırarak PROJECT.md'yi doldurun.
```
**ABORT and stop.**

---

## PROCEDURE

### 1. Parse Argument

User provides either:
- **Path:** `/analyze-data data/vibration.csv`
  - Trigger: exploratory data analysis (EDA)
  
- **Task description:** `/analyze-data "train CNN model for fault detection"`
  - Trigger: specific analysis task

### 2. Prepare Input for data-scientist Agent

Compose the subagent input contract:

```
Task: [from argument or ask user]
Data path(s): <paths under analysis/> or to be copied there
RQs from PROJECT.md: [list]
Target venue: [from PROJECT.md if known]
Requested outputs:
  - EDA: yes (if path given) / no
  - Model training: yes/no [ask if task is vague]
  - Figures: yes [always] — prefer PDF + PNG at 300 dpi
  - Tables: yes [always] — CSV + LaTeX/Excel format
  - Reproducibility: yes [always] — scripts + environment + seeds

Data dictionary (if available): [description of columns, units, missing-value policy]
```

**Ask user for clarification:**
```
Analiz türü:
1) Keşfedici veri analizi (EDA)
2) İstatistiksel testler (t-test, ANOVA, vb.)
3) Model eğitimi ve değerlendirmesi
4) Belirli görevler (hangi?)

Lütfen seçin veya görevin açıklamasını yazın:
```

Also ask:
```
Veri sözlüğü? (sütun adları, birimler, eksik değer politikası)
[input veya: hayır, ayrıntı yoktur]

Hedef dergi stil kuralları? (figür boyutu, renk şeması, vb.)
[input veya: varsayılan kullan]
```

### 3. Dispatch data-scientist Agent

Call with:
- Task (full description or data path + EDA request)
- RQs from PROJECT.md
- Data locations
- Style requirements

**Expected return:**
- File paths produced (scripts, figures, tables, captions)
- Numeric-results digest (headline numbers, max ~15 lines)
- Own-result card IDs created (EV-####)
- Reproducibility note (how to re-run)

### 4. Receive and Verify Results

Agent returns:
```
Files created:
  - analysis/01_eda.py (script)
  - analysis/figures/distribution.pdf (300 dpi)
  - analysis/figures/distribution.png (web-safe)
  - analysis/tables/summary_stats.csv
  - analysis/captions.md (figure/table captions)
  - analysis/RUNLOG.md (reproducibility info)

Results (headline digest):
  Dataset: N=1250 samples, p=15 features
  Missing: 2.3% (imputed via KNN)
  Class distribution: 60% normal, 40% faulty
  
  Model performance (10-fold CV, seeds 42–51):
    CNN: 94.2 ± 2.1% accuracy, F1=0.92 ± 0.03
    SVM: 89.5 ± 3.0% accuracy, F1=0.86 ± 0.05
  
  Ablation (CNN, removing components):
    - No attention: 91.8% → attention contributes 2.4%
    - No batch norm: 87.3% → batch norm contributes 6.9%

Card IDs created: EV-0087, EV-0088, EV-0089 (own-result type)

Reproducibility: `python analysis/01_eda.py` (seed 42) reproduces figures.
```

**Verify own-result cards were registered:**
```bash
python scripts/evidence_db.py query --type own-result
```

Check: do the new card IDs appear? Print count:
```
✅ Kanıt kartları kaydedildi: [N] yeni own-result kartı
   (EV-0087, EV-0088, EV-0089, ...)
```

### 5. Surface Numeric Digest & File Paths

Print to user:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Veri analizi tamamlandı!

Sonuçlar (özet):
───────────────────────────────────────────────────
Dataset:
  Örneklem sayısı: 1,250
  Özellik sayısı: 15
  Eksik değer: 2.3%
  Sınıf dağılımı: 60% normal, 40% arızalı

Model Performansı (10-katlı çapraz doğrulama):
  CNN:
    Doğruluk: 94.2 ± 2.1%
    F1 puanı: 0.92 ± 0.03
    Eğitim süresi: 2m 34s
  
  SVM (temel çizgi):
    Doğruluk: 89.5 ± 3.0%
    F1 puanı: 0.86 ± 0.05

Ayrıntı çalışması:
  Dikkat mekanizması: +2.4% iyileştirme
  Toplu normalizasyon: +6.9% iyileştirme

Yaratılan Kanıt Kartları:
  EV-0087: CNN modeli performansı
  EV-0088: Ayrıntı analizi sonuçları
  EV-0089: Toplu veri istatistikleri

Çıktı Dosyaları:
  Figürler:
    analysis/figures/learning_curve.pdf (300 dpi)
    analysis/figures/learning_curve.png (web)
    analysis/figures/confusion_matrix.pdf
    analysis/figures/confusion_matrix.png
    ... [full list]
  
  Tablolar:
    analysis/tables/model_comparison.csv
    analysis/tables/model_comparison.tex (LaTeX)
    analysis/tables/hyperparameters.csv
    analysis/tables/ablation_results.csv
    ... [full list]
  
  Betikler (yeniden üretilebilir):
    analysis/01_eda.py
    analysis/02_train_cnn.py
    analysis/03_ablation.py
    analysis/RUNLOG.md (ortam + komutlar)

Yeniden Üretim:
  python analysis/01_eda.py          # EDA'yı yeniden çalıştır
  python analysis/02_train_cnn.py    # CNN modelini yeniden eğit (seed 42–51)
  # Tam durum: analysis/RUNLOG.md dosyasına bakın
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6. Citation Note

Remind user:
```
ℹ️ Results Bölümü Yazarken:
   - Bu figürler ve tablolar, literatür gibi kanıt kartları aracılığıyla alıntılanır.
   - Örnek: "CNN modeli ortalama 94.2% doğruluk elde etti [@EV-0087]."
   - Own-result kartları, dış kaynaklar gibi kaydedilir.

Yazı Örneği:
   "Ours, state-of-the-art CNN'ler ve geleneksel baseline'lar karşılaştırdık.
    Sonuçlar Tablo X'te gösterilmektedir [@EV-0088].
    CNN modeli 94.2% doğruluk elde ederken [@EV-0087], 
    SVM baseline 89.5% elde etti [@EV-0089]."
```

### 7. Next Steps Suggestion

```
Sonraki Adımlar:
  1. /draft results — Results bölümünü yazarken figür/tablo kartlarını kullanın
  2. /outline — iskelet henüz yoksa oluşturun; bu kartlar Results bölümüne bağlanacak
  3. /export-excel — analiz sonuçlarını Excel'e aktarın
```

---

## GATES SUMMARY

| Gate | Trigger | Action |
|------|---------|--------|
| PROJECT.md TBD fields | Yes | ABORT, explain which fields need filling |
| Data path not found | Yes | ABORT, ask user to verify path or copy data to analysis/ |
| Analysis task too vague | Yes | WARN, ask for clarification (EDA? model? specific task?) |

---

## ARGUMENT EXAMPLES

```
/analyze-data data/vibration.csv
/analyze-data "train CNN for bearing fault detection"
/analyze-data analysis/experiment-results.csv
/analyze-data "compare 3 model architectures on balanced vs imbalanced data"
```

---

## SCRIPT USAGE (by data-scientist agent, not by user)

Agent will use:
```bash
python analysis/01_eda.py          # reads from analysis/, writes figures + tables
python analysis/02_train_models.py # trains CNN, SVM, etc.; logs results
python scripts/evidence_db.py add --stdin  # register own-result cards

# User may re-run later:
python analysis/01_eda.py          # regenerates figures if data/code unchanged
```

---

## TOKEN ECONOMY NOTES

- **Subagent runs locally** inside analysis/ directory.
- **Verbose outputs** (dataframes, training logs, tracebacks) die in subagent's context.
- **Only numeric digest + file paths return** (~200 tokens).
- **Full reproducibility:** scripts on disk can be re-run without subagent.

---

## ERROR MESSAGES (Turkish)

```
❌ PROJECT.md tamamlanmamış. Lütfen /new-project çalıştırın.
❌ Veri dosyası bulunamadı: [path]. Lütfen dosya yolunu kontrol edin.
⚠️ Analiz görev açıklaması çok vague. Açıklayınız:
   1) EDA (keşfedici veri analizi)
   2) Model eğitimi
   3) Belirli görev (detay yazın)
```

---

## FOLLOWING STEPS

After `/analyze-data`:
- User runs `/draft results` to write Results section, citing own-result cards.
- User may run `/export-excel` to create summary tables for presentation/reviewer.
- All figures/tables can be embedded in final paper via standard referencing mechanisms.
