/**
 * Single source of truth for everything the site states about the kit.
 *
 * Prose lives in the pages; anything that is a *fact about the repository*
 * lives here, so a number appears once. `tests/test_governance_docs.py`
 * re-derives several of these from the repository itself and fails the build
 * when they drift — the tool list against `scripts/`, the version against
 * `CITATION.cff`, the domain against `docs/CNAME`.
 */

export const SITE = {
  domain: 'scholar.mtvrkan.com',
  url: 'https://scholar.mtvrkan.com',
  repo: 'https://github.com/mtvrkan/scholar-kit',
  version: '1.0.0',
  // Passing tests on a default `python -m pytest` (live-network tests excluded).
  // Derived from a real collection run by test_governance_docs.py, which is what
  // stops this from becoming the stale number it was before.
  tests: 2390,
  tools: 68,
  agents: 10,
  commands: 43,
  knowledge: 11,
  // Registered hook entries in .claude/settings.json — NOT the file count in
  // .claude/hooks/, which also holds underscore-prefixed shared libraries
  // (_shell_write_sink, _project_scope, _degrade) that no event ever invokes.
  // Counting files said 7 for months. test_governance_docs.py now derives this
  // from settings.json so it cannot drift again.
  hooks: 6,
} as const;

export const GH = SITE.repo + '/blob/main';

/* One page, five anchors. The site was five documents that repeated a masthead,
   a footer and a language toggle between them, and every move between two of
   them cost a full navigation to read four more sections of the same argument.
   The hrefs stay relative so the page still works opened from disk.

   The slugs are English on a page whose first language is Turkish, and that is
   the right way round: a fragment is not prose, it is an identifier that ends
   up pasted into issues, chat and other people's documents, where `#genel-bakis`
   is a string nobody outside one language can read back. The LABELS are still
   translated — those are what the reader sees.

   `#vitrin` went when the showcase did — leaving the entry behind would have
   been the quiet kind of breakage, a masthead link that scrolls nowhere, which
   no build step notices. `#faq` took the slot, and it is the better tenant: it
   is where a reader who is not yet convinced actually wants to go, and it was
   the one band on the page with no way to reach it except scrolling. */
export const NAV = [
  { href: '#overview', tr: 'Genel bakış', en: 'Overview' },
  { href: '#gates', tr: 'Kapılar', en: 'Gates' },
  { href: '#how-it-works', tr: 'Nasıl çalışır', en: 'How it works' },
  { href: '#install', tr: 'Kurulum', en: 'Install' },
  { href: '#faq', tr: 'SSS', en: 'FAQ' },
] as const;

export type Bi = { tr: string; en: string };

// ── commands ───────────────────────────────────────────────────────────────
// `gate` is the precondition the hook layer enforces before the command will
// start. An empty gate means it runs at any time — that is information, not a
// missing value, which is why it renders as a dash rather than blank.

/* The command table, the knowledge-skill table, the subagent table and the
   refused-mechanisms table used to live here, feeding four reference chapters.
   The site is an introduction now and those chapters are the README's job, so
   the data went with them — a module that exports what nothing renders is the
   next thing to go stale. */

export const GATES: (Bi & { name: string })[] = [
  { name: 'outline → onay / approval',
    tr: 'Kanıt kartlarına bağlanmış iskelet onaylanmadan hiçbir bölüm yazılmaz.',
    en: 'No section is drafted before the card-bound skeleton is approved.' },
  { name: 'verify = PASS',
    tr: 'Atıf doğrulaması geçmeden hakem turu açılmaz: uydurma atıf, geri çekilmiş makale, eksik künye.',
    en: 'No review round opens until citation verification passes: fabricated citations, retractions, missing entries.' },
  { name: 'Major = 0',
    tr: 'Hakem simülasyonunda açık Major bulgu varken biçimlendirme başlamaz.',
    en: 'Formatting does not begin while the peer review has open Major findings.' },
];
