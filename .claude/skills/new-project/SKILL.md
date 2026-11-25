---
name: new-project
description: "Initialize a new research project by copying the template, then run an interactive wizard to fill PROJECT.md with conversation language, topic, research questions, paper/thesis type, target venue, citation style, output language, search languages, word budget, and deadline."
disable-model-invocation: true
argument-hint: "[type] [subdir]"
---

# Initialize a New Project

This skill creates a new project directory and guides you through the initial scoping: topic definition, research questions, output format selection, and word budget allocation.

## PROCEDURE

### 1. Check for Existing Project (GATE)

**Check:** Does PROJECT.md exist in current directory or in [subdir]?
- If YES and it has real content (not all TBD): **ABORT**. This fires before
  Field 0 (Conversation Language) is ever asked, so print bilingually:
  ```
  ❌ Bu dizinde zaten doldurulmuş bir PROJECT.md var. Yeni bir proje için:
  1. Başka bir dizine geçin veya
  2. /new-project subdir-adi komutuyla yeni alt dizin oluşturun veya
  3. Mevcut PROJECT.md dosyasını silip yeniden başlayın.

  ❌ A filled-in PROJECT.md already exists in this directory. For a new project:
  1. Switch to another directory, or
  2. Create a new subdirectory with /new-project <subdir-name>, or
  3. Delete the existing PROJECT.md and start over.
  ```
- If NO or [subdir] does not exist: proceed.

### 2. Copy Template — projects are SELF-CONTAINED

A project must work as its own Claude Code (or Codex) workspace, so it needs the kit runtime,
not just the data skeleton. Locate the kit root — call it $KIT: walk up from
this skill's own directory (`.claude/skills/new-project/`, or
`codex/skills/new-project/` under Codex) to the directory that contains
`project-template/`.

1. Target: `<subdir>/` if provided (`mkdir -p <subdir>`), else the current directory.
   The target must NOT be inside $KIT/project-template.
2. Copy INTO the target:
   - `$KIT/project-template/*`  (PROJECT.md, sources/, evidence/, analysis/, bib/,
     outline/, drafts/, reviews/, exports/, build/, and the non-manuscript axes:
     proposal/, teaching/, dossier/)
   - `$KIT/CLAUDE.md`           (constitution — sessions in the project dir load it)
   - `$KIT/.claude/`            (agents, skills, hooks, settings.json)
   - `$KIT/scripts/`            (all `python scripts/...` calls resolve locally)
   - `$KIT/templates/`          (CSL styles, reference.docx, thesis skeletons)
3. Do NOT copy: `$KIT/data/` (large index datasets — instead, if `$KIT/data/*.csv`
   exists, create a small pointer so venue_check finds it:
   on any OS run `python -c "import pathlib;
   pathlib.Path('data').mkdir(exist_ok=True)"` then copy the CSVs OR tell the user
   to re-run `bash INSTALL.sh --update-data` inside the project. Prefer copying if
   disk allows; datasets are per-machine, not per-project.)
4. If target == current directory AND it already IS the kit root (CLAUDE.md +
   scripts/ present), skip copying runtime files — only copy `project-template/*`.
5. **Patch the hook interpreter in the copied settings.json.** The copied
   `.claude/settings.json` wires every hook to a literal interpreter name
   (`python`). On a machine where only `python3` or `py` resolves, every hook
   fails to launch — and `PreToolUse` hooks fail OPEN, so enforcement is silently
   absent rather than noisily broken. `bash INSTALL.sh` does this for a cloned
   kit; a project created from a **plugin** install never runs INSTALL, so do it
   here. From the target directory, detect the working interpreter and run:
   ```bash
   python scripts/patch_hook_interpreter.py --target <python|python3|py>
   ```
   Use whichever of `python` / `python3` / `py` actually launched the command.
   Skip only when step 4 applied (the kit root is already patched).
6. **Wire the Codex side to the same interpreter.** From the target directory:
   ```bash
   python scripts/codex_sync.py --project --python <python|python3|py>
   ```
   Run it whichever harness you are in, so the project works in both. It
   GENERATES, from the `.claude/` and `templates/` just copied, everything
   OpenAI Codex reads at its fixed project paths: `AGENTS.md` (the same
   constitution), `.codex/hooks.json` + the adapter (the same gates),
   `.codex/agents/`, `.codex/rules/` and `.agents/skills/`. Do not copy
   `$KIT/codex/` instead — that folder is the kit's own layout, not a
   project's. Skip only when step 4 applied.
7. Confirm: "Project initialized at `<path>` (self-contained: runtime + templates
   copied, hooks wired to `<interpreter>`). Open Claude Code or Codex IN this
   directory for all project work." When running under Codex, add: "Codex runs
   a hook only after you have reviewed it — trust this project, then open
   `/hooks` once and approve the Scholar-Kit gates. Until then the phase gates
   and data-file protection are guidance, not gates."

### 3. Run Interactive Wizard

Walk the user through each field of PROJECT.md (present each as a numbered choice or text entry).
Ask **Field 0 first, before anything else** — it decides which language the
rest of this wizard (and every later skill's gates/aborts/summaries) is
conducted in.

**Field 0: Conversation Language**
```
Hangi dilde konuşalım? / Which language should we work in?
1) Türkçe (varsayılan / default)
2) English

Seçiminiz / Your choice: <input>
→ Write "tr" or "en" to the `- **Conversation language:**` bullet.
→ From THIS POINT ON — the rest of this wizard, and every other skill's
  user-facing text for the life of the project — conduct in the chosen
  language. Every other skill's SKILL.md writes its gate/abort/summary
  messages in Turkish as the kit's default; when Conversation language is
  "en", present the equivalent content in natural English (translate
  meaning and structure — headings, bullet shape, ✅/❌ markers — rather
  than reproducing the Turkish text verbatim). This is orthogonal to
  Output language (Field 6 below): Conversation language governs how the
  assistant talks to the user; Output language governs the language the
  manuscript itself is drafted in — a thesis can be drafted in English
  while the working conversation stays in Turkish, or vice versa.
```

**Field 1: Topic (Turkish or English)**
```
Konunuz nedir? (örnek: "CNN tabanlı rulman arıza teşhisi")
→ Validate: not empty, not single word. If unclear: ask for 1–2 more sentences of context.
→ Write to PROJECT.md's Identity section, `- **Title (working):**` bullet.
```

**Field 2: Research Questions (≥1, ≤4)**
```
Araştırma sorularınız nelerdir? (satır satır girin, sonra boş satır ile tamamlayın)
RQ1: <input>
RQ2: <input>
...
→ Validate: each ≥10 words, ends with "?". If fewer than 1 or >4: ask to reconsider.
→ Write: one `  - RQ<n>: <text>` bullet per RQ under "Research questions:" —
  this exact bullet shape (leading `-`, `RQ<n>:` prefix) is what
  word_budget.py --rq-trace's regex matches; do not reformat it.
```

**Field 3: Paper/Thesis Type**
```
Çıktı türü:
1) makale (IMRaD) / article (empirical)
2) sistematik derleme / systematic review
3) derleme (tematik) / narrative review
4) scoping derleme / scoping review
5) niteliksel çalışma / qualitative study
6) tez (BSc/MSc/PhD)
7) konferans bildirisi / conference paper
8) diğer (hangi?)

Seçiminiz: <input>
→ Validate against paper-types skill list. If invalid: show list again.
→ Write to the `- **Type:**` bullet (keep the `**bold**` markers — word_budget.py's
  regex matches on them). Use the paper-types enum key, not the numbered label
  (e.g. "empirical-imrad", not "makale (IMRaD)").
```

**Field 4: Target Venue**
```
Hedef dergi/konferans/kurum (adı veya ISSN; isteğe bağlı):
<input>
→ If provided: suggest running `/journal-check "<input>"` after wizard.
→ Write to the `- **Target venue:**` bullet.
```

**Field 5: Citation Style**
```
Atıf stili:
1) APA 7
2) IEEE
3) Chicago (Author-Date)
4) Vancouver/AMA
5) Harvard
6) MLA 9
7) özel CSL (provide CSL file later)

Seçiminiz: <input>
→ Validate against citation-styles skill list.
→ Write to the `- **Citation style:**` bullet using the enum key (apa7 | mla9 |
  chicago-author-date | chicago-notes | ieee | vancouver | harvard | csl:<file>) —
  the same key citation-styles' CSL filename map (Section "CSL File Mapping")
  resolves at render time.
```

**Field 6: Output Language**
```
Akademik çıktının dili:
1) English (İngilizce)
2) Türkçe
3) Her ikisi (Özet + Abstract)

Seçiminiz: <input>
→ Write to the `- **Output language:**` bullet as "tr", "en", or "both".
```

**Field 7: Search Languages (for literature review)**
```
Literatür taraması hangi dillerde yapılsın?
1) İngilizce (EN)
2) Türkçe (TR)
3) Her ikisi (EN + TR) [önerilir]

Seçiminiz: <input>
→ Explain: "EN tabanlı konular: her ikisi önerilir. Türkiye-spesifik konular: TR zorunlu."
→ Write to the `- **Search languages:**` bullet as "tr", "en", or "both". This
  sets the default the bilingual decision matrix (literature-review skill)
  starts from — literature-scout may still override per-topic and must log why.
```

**Field 8: Word Budget (approximate total)**
```
Yaklaşık hedef sözcük sayısı (örnek: 6500, 40000, vb.):
<input>
→ Validate: numeric, 1000–200000. If outside: suggest reasonable range for type.
→ Write to the `- **Word budget (total):**` bullet as a plain integer (no
  thousands separator inside the value word_budget.py's regex captures — e.g.
  "6500", not "6.500" — the script strips commas/dots for TR-locale input but
  writing the clean digit string avoids relying on that).
```

**Field 9: Deadline (optional)**
```
Teslim tarihi (YYYY-MM-DD) [isteğe bağlı]:
<input>
→ Validate: if provided, must be future date. If past: warn and ask to confirm.
→ Write to the `- **Deadline:**` bullet (or leave "TBD" if blank).
```

### 4. Summary & Confirmation

Display a summary table (in the Field-0 conversation language):
```
PROJECT SUMMARY
───────────────────────────────────────
Conversation Lang:  [tr|en]
Topic:              [user topic]
RQs:                [count]
Type:               [type]
Target Venue:       [venue or "TBD"]
Citation Style:     [style]
Output Language:    [lang]
Search Languages:   [langs]
Word Budget:        [count] words
Deadline:           [date or "No deadline"]
───────────────────────────────────────
```

Ask: "Doğru mu? (evet/hayır)"
- **evet**: proceed to step 5.
- **hayır**: ask which field to re-enter and loop back to that field.

### 5. Write PROJECT.md

`project-template/PROJECT.md` was already copied into the project root in
Step 2. **Edit that file in place** (Edit tool, not a rewrite) — fill each
`TBD` with the wizard's answer, keeping the section headings, HTML comments,
and `- **Label:**` bullet shapes byte-for-byte as shipped in the template.

**Do NOT rewrite it as YAML.** `word_budget.py` (`--rq-trace` and the plain
budget report) parses this file with regexes anchored to the Markdown
bold-label format — `Word budget \(total\):\*{0,2}`, `\*\*Type:\*\*`, and
`^\s*[-*]\s*(RQ\d+)\s*:` for the RQ bullets. A YAML version matches none of
these: every RQ trace and word-budget check would silently return
empty/`None` for the life of the project.

Field → template-bullet mapping (all under existing section headings — do
not add new ones):
```
conversation_lang -> ## Languages         - **Conversation language:**
topic            -> ## Identity          - **Title (working):**
type             -> ## Identity          - **Type:**
RQs              -> ## Identity          - **Research questions:** (one `  - RQ<n>: <text>` bullet each)
target_venue     -> ## Target & format   - **Target venue:**
citation_style   -> ## Target & format   - **Citation style:**
output_language  -> ## Languages         - **Output language:**
search_languages -> ## Languages         - **Search languages:**
word_budget      -> ## Budget & schedule - **Word budget (total):**
deadline         -> ## Budget & schedule - **Deadline:**
```

Leave `- **Per-section budgets:** auto`, `- **Template:** none`,
`- **Own data:** none`, `- **Compute notes:** TBD`, and `- **Phase:** scoping`
exactly as shipped — later skills/scripts update them, the wizard does not.
Append a trailing HTML comment (invisible to the
regex parsers, but useful for humans) recording creation time:
```markdown
<!-- created_at: <ISO timestamp> -->
```

### 6. Final Message

Print to user, in the Field-0 conversation language (Turkish shown; if "en"
was chosen, translate meaning/structure rather than reproducing this text):
```
✅ Proje başlatıldı! 

Sonraki adımlar:
1. Hedef dergisi için: /journal-check "<venue>"
2. Literatür taraması başlatmak için: /lit-review [--systematic]
3. Proje durumu: /status

Açılış PROJECT.md: <path>/PROJECT.md
```

---

## GATES SUMMARY

| Gate | Trigger | Action |
|------|---------|--------|
| Existing filled PROJECT.md | Yes | ABORT with Turkish explanation; offer alternatives |
| Topic empty/too short | Yes | REJECT, ask for clarification |
| RQ count invalid | <1 or >4 | REJECT, explain reasoning |
| RQ quality | Single word / <10 words | WARN, suggest clarification |
| Type invalid | Not in paper-types list | ABORT, show options |
| Style invalid | Not in citation-styles list | ABORT, show options |
| Lang invalid | Not EN/TR/both | ABORT, show options |
| Word budget invalid | <1000 or >200000 | WARN, suggest range for type |
| Deadline invalid | Past date | WARN, ask to confirm |

---

## ERROR MESSAGES (Turkish default — translate to English when Field 0 is "en")

```
❌ Topic başlığınız çok kısa. Lütfen en az bir cümle yazın.
❌ RQ sayısı 1–4 arasında olmalı. Kaç tane RQ'nuz var?
❌ Atıf stili tanınmıyor. /citation-styles skill'ine bakarak desteklenen stilleri görün.
❌ Bu dizinde zaten doldurulmuş PROJECT.md var.
```

---

## SCRIPT USAGE

None. This is a pure wizard. No Python scripts run in this step.

---

## FOLLOWING STEPS

After PROJECT.md is created:
- User may run `/journal-check` to verify target venue quality.
- User may run `/lit-review` to start literature search.
