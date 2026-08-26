"""The site's own assertions — everything that reads `docs/`.

Split out of `test_governance_docs.py` so the website can live on its own branch
without taking the kit's test suite with it, and without leaving twenty-six
tests on `main` that fail the moment `docs/` is not there.

What they check is unchanged: that the BUILT output states facts this repository
can re-derive. They import those derivations rather than copying them, because
two copies of "how many hooks are registered" is exactly the drift the whole
file exists to catch.
"""
import re

import pytest

from test_governance_docs import (
    ROOT,
    _cff,
    _csp,
    _INLINE_SCRIPT,
    _registered_hooks,
    _site_number,
    _site_ts,
)

# ---------- the site ----------

SITE = ROOT / "docs" / "index.html"
SITE_DIR = ROOT / "docs"
# One page. The site was five documents that repeated a masthead and a footer
# between them; what the assertions below check is unchanged — that the BUILT
# output states a fact the repository can re-derive — only where they look.
SITE_PAGES = ("index.html",)


def _pages():
    return {n: (SITE_DIR / n).read_text(encoding="utf-8") for n in SITE_PAGES}



def test_the_stylesheet_never_unpositions_an_element():
    """`position: static` has cost this design two visible defects, both the
    same shape, and neither of them looked like a positioning bug.

    Taking `position` off an element also takes it off every absolutely
    positioned thing INSIDE it: the containing block silently becomes whatever
    positioned ancestor is next up the tree. A button's hover shine, parked at
    `translateX(-130%)` and `inset: 0`, painted a metre-wide diagonal band
    across the page. A margin note's 2px rule, written `inset-block: 0` to sit
    beside one 61px note, was drawn 257px down the whole annotated block
    starting above the paragraph, beside nothing.

    In both cases the intent was "put this back in the flow", and in both cases
    `relative` says exactly that while keeping the element a containing block.
    So the rule here is: this stylesheet does not unposition. If a future edit
    genuinely needs `static`, it needs to state why here first — which is the
    review this gate exists to force, not a ban on the keyword.
    """
    css = (ROOT / "web" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    hits = [ln.strip() for ln in css.splitlines() if re.search(r"position:\s*static", ln)]
    assert not hits, (
        "global.css unpositions an element, which re-parents every absolutely "
        f"positioned descendant: {hits}. `position: relative` restores flow "
        "placement without giving that away.")


def test_every_custom_property_the_stylesheet_uses_is_one_it_defines():
    """A `var(--x)` naming a token that does not exist fails silently.

    It does not throw, it does not warn, and it does not fall back to anything
    useful: the whole declaration is dropped at computed-value time, so the
    property reverts to its initial value and only that one property does. The
    rest of the rule applies normally, which is what makes it hard to see — a
    panel keeps its border, its radius and its background and simply has no
    padding, and the page looks like a spacing decision somebody made.

    This was not hypothetical. The spacing scale runs 1 2 3 4 6 8 12 16 24 32,
    with no 5 and no 10, and a round of edits wrote `var(--s5)` and `var(--s10)`
    in six places — including the rule whose entire job was to fix a panel that
    had no space under it. The fix built, shipped and did nothing.

    Definitions are collected from anywhere in the file, so a token defined only
    inside a media query still counts; the failure this catches is a NAME that
    exists nowhere, which is the one a browser cannot tell you about.
    """
    css = (ROOT / "web" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    defined = set(re.findall(r"(?<!var\()(--[a-z0-9-]+)\s*:", css))
    used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)", css))
    missing = sorted(used - defined)
    assert not missing, (
        f"global.css uses custom properties it never defines: {missing}. "
        f"Every declaration naming one of these is dropped by the browser.")


def test_the_readmes_share_card_is_the_one_the_site_serves():
    """A README image is the first thing on the repository page and the easiest
    thing to leave pointing at a file that moved. It is referenced by absolute
    URL on purpose — the built site is not always on the same branch as this
    file — so what is checkable here is that each card exists in the build and
    that each README points at the domain the site declares.

    Two cards, one per language, and the pairing is the point: the English
    README is an English document read by English readers, and it opened with a
    Turkish headline for as long as there was only one card to open with.
    """
    host = "https://" + (ROOT / "docs" / "CNAME").read_text(encoding="utf-8").strip()
    for name, image in (("README.md", "og-en.png"), ("README.tr.md", "og.png")):
        card = f"{host}/{image}"
        text = (ROOT / name).read_text(encoding="utf-8")
        assert card in text, f"{name} does not show {card}"
        assert (ROOT / "docs" / image).exists(), (
            f"{name} points at {image}, which is not built — run "
            f"`python web/make_og.py` and rebuild the site")


# ---------- the site ----------

SITE = ROOT / "docs" / "index.html"
SITE_DIR = ROOT / "docs"
# One page. The site was five documents that repeated a masthead and a footer
# between them; what the assertions below check is unchanged — that the BUILT
# output states a fact the repository can re-derive — only where they look.
SITE_PAGES = ("index.html",)
def test_site_lives_where_github_pages_can_serve_it():
    # Pages serves a branch folder only from the repo root or /docs. A page in
    # site/ would need a workflow; this layout needs none, and moving it back
    # would silently break the deploy without breaking anything visible here.
    assert SITE.exists(), "docs/index.html is missing — Pages has nothing to serve"
    assert (ROOT / "docs" / "CNAME").exists()
def test_site_cname_matches_the_domain_the_page_declares():
    # Three places state the domain: CNAME, the canonical link, and og:url.
    # Any two disagreeing produces a live site that de-indexes itself.
    domain = (ROOT / "docs" / "CNAME").read_text(encoding="utf-8").strip()
    assert domain and " " not in domain and "/" not in domain, f"bad CNAME: {domain!r}"
    html = SITE.read_text(encoding="utf-8")
    canonical = re.search(r'rel="canonical"\s+href="https://([^/"]+)', html)
    og_url = re.search(r'property="og:url"\s+content="https://([^/"]+)', html)
    assert canonical and og_url, "the page declares no canonical/og:url"
    assert canonical.group(1) == domain, (
        f"canonical is {canonical.group(1)} but CNAME says {domain}")
    assert og_url.group(1) == domain
def test_site_is_self_contained():
    # A strict-CSP host is not the constraint here, but the claim in both READMEs
    # is "single file, no dependencies, no build step". An external stylesheet,
    # script or font URL would quietly make that false.
    # `rel="canonical"` is metadata, not a fetch — it names the page's own
    # address and must stay absolute. Only tags the browser would actually load
    # from count: scripts, stylesheets, preloads, fonts.
    html = SITE.read_text(encoding="utf-8")
    fetched = re.findall(r'<script[^>]+src="(https?://[^"]+)"', html)
    fetched += [m.group(2) for m in re.finditer(
        r'<link[^>]*rel="(stylesheet|preload|prefetch|preconnect)"[^>]*href="(https?://[^"]+)"',
        html)]
    assert not fetched, f"the page pulls external assets: {fetched}"
    assert "@import" not in html, "the page imports an external stylesheet"
def test_the_policy_names_no_remote_host():
    """The CSP is where "no outbound request" is either true or a slogan.

    `test_site_is_self_contained` above reads the TAGS on the page, so it can
    only see a fetch that is spelled out in markup. It could not see the site's
    actual outbound request: a `media-src` directive naming a CloudFront
    distribution, added for a fullscreen backdrop video whose asset this project
    did not own and which — recorded in web/DESIGN.md at the time — had never
    once been seen rendering, because the CDN was unreachable from the machine
    the site was built on. The claim in both READMEs had to be softened to "one
    outbound request" to stay honest, on the marketing site of a kit whose
    SECURITY.md opens with *what leaves your machine*.

    The backdrop is gone. This reads the policy itself rather than the markup,
    so the softening cannot happen again without a test going red first: no
    directive may name a scheme-qualified host. `data:` stays allowed — it is
    the inline SVG favicon and it fetches nothing.
    """
    for name, html in _pages().items():
        m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
        assert m, f"{name} carries no CSP"
        for directive in m.group(1).split(";"):
            assert "//" not in directive, (
                f"{name}'s CSP names a remote host in `{directive.strip()}` — "
                f"the site is meant to fetch nothing it does not ship")
def test_the_landing_description_states_no_stale_counts():
    """The one published number with no test, found by reading the page.

    Four of the five pages interpolate their meta description from `SITE`.
    index.astro hard-coded its counts, and so shipped "9 subagent, 17 komut"
    against a real 10 and 43 — in `<meta name="description">`, which is the text
    a search result and every shared link shows. Nothing here read that string,
    because every other governance test reads the VISIBLE page.

    Rather than pin the sentence, this pins the property that made it wrong:
    every integer in the landing description must be a number the repository
    actually reports. A count typed by hand fails on the first drift.
    """
    html = SITE.read_text(encoding="utf-8")
    m = re.search(r'<meta name="description" content="([^"]+)"', html)
    assert m, "the landing page states no meta description"
    desc = m.group(1)
    known = {_site_number(f) for f in ("tools", "tests", "agents", "commands",
                                       "knowledge", "hooks")}
    stated = {int(n) for n in re.findall(r"\b(\d+)\b", desc)}
    unknown = stated - known
    assert not unknown, (
        f"the landing description states {sorted(unknown)}, which no SITE field "
        f"reports (known: {sorted(known)}) — interpolate from site.ts instead of "
        f"typing a count: {desc!r}")
def test_the_site_is_ready_to_publish():
    """The handful of publication facts no other test here owns.

    Each of these is invisible until somebody else sees it: a share card built
    from an older palette, a broken link whose unfurl is a bare URL, a sitemap
    reference pointing at a file that is not deployed. They are cheap to check
    and expensive to notice — the noticing is done by a stranger, on a link
    that has already been sent.
    """
    docs = ROOT / "docs"
    for image in ("og.png", "og-en.png"):
        card, source = docs / image, ROOT / "web" / "public" / image
        assert card.exists() and source.exists(), f"the share card {image} is missing"
        assert card.read_bytes() == source.read_bytes(), (
            f"docs/{image} differs from web/public/{image} — the card was "
            f"regenerated and the site was not rebuilt, so the live unfurl is "
            f"the old one")

    notfound = (docs / "404.html").read_text(encoding="utf-8")
    assert "noindex" in notfound, "the 404 would be indexed"
    assert 'property="og:image"' in notfound, (
        "the 404 carries no share card. It is not indexed and it is still "
        "shared — a broken link pasted into a chat unfurls as a bare URL")

    robots = (docs / "robots.txt").read_text(encoding="utf-8")
    m = re.search(r"Sitemap:\s*https?://[^/]+/(\S+)", robots)
    assert m, "robots.txt names no sitemap"
    assert (docs / m.group(1)).exists(), (
        f"robots.txt points at {m.group(1)}, which is not in docs/")


def test_the_hero_pipeline_names_real_commands():
    """The first screen prints six slash commands. Every one has to exist.

    A landing page that invents a command is the exact failure this kit is
    built to refuse, committed by its own marketing — and it is the kind that
    survives review, because a plausible name reads as a real one. The skill
    directory is the registry: a command is a directory under `.claude/skills/`
    with a `SKILL.md` in it, so the check is against the thing that actually
    ships rather than against a list somebody keeps in step by hand.
    """
    src = (ROOT / "web" / "src" / "components" / "Pipeline.astro").read_text(encoding="utf-8")
    named = sorted(set(re.findall(r"cmd:\s*'/([\w-]+)'", src)))
    assert named, "the hero pipeline names no commands — has the panel changed?"
    skills = ROOT / ".claude" / "skills"
    missing = [c for c in named if not (skills / c / "SKILL.md").exists()]
    assert not missing, (
        f"the hero pipeline prints {['/' + c for c in missing]}, which the kit "
        f"does not ship. Rename them to real commands or remove the rows.")


def test_the_site_claims_no_run_it_cannot_show():
    """The showcase band and its three run cards are gone, and this is what
    stops them coming back as prose.

    `test_the_run_figures_come_from_the_runs` stood here and bound each card's
    verified-citation count to that run's own `03-verify-status.json`, so the
    page could not state a figure the artifact did not. The artifacts have been
    withdrawn — two of the three runs never reached a result their author would
    stand behind — and the same failure is now available in a quieter form: a
    sentence about three real papers, with nothing in the repository behind it.
    A claim whose evidence has been deleted is worse than no claim.
    """
    html = SITE.read_text(encoding="utf-8")
    assert "examples/showcase" not in html, (
        "the built page links examples/showcase, which no longer ships — "
        "rebuild with `npm --prefix web run build`")
    assert 'id="vitrin"' not in html, "the showcase band is back on the built page"


def test_the_built_stylesheet_keeps_the_standard_property_beside_every_prefixed_one():
    """A vendor prefix alone is a bet that the alias outlives the standard, and
    that bet has already been lost once here.

    Astro 7 changed the default CSS minifier to Lightning CSS, which does not
    merely compress: it rewrites declarations against its browser targets. On
    the defaults it replaced every `backdrop-filter` with
    `-webkit-backdrop-filter` and dropped the standard property — and current
    Chrome no longer answers to that alias, so the declaration resolved to
    nothing. Every glass surface on the page lost its blur at once: the masthead
    pane, the lit navigation item, the figure strip. The build was green, all of
    this suite was green, and nothing anywhere reported an error; the only
    symptom was that the design had quietly stopped being made of glass.

    So the rule is the general one rather than a patch for `backdrop-filter`:
    whatever the minifier is, if the built stylesheet declares a `-webkit-`
    property it must also declare the unprefixed one somewhere. That catches the
    next property this happens to without anyone having to predict which.
    """
    css_files = sorted((ROOT / "docs" / "assets").glob("*.css"))
    assert css_files, "no built stylesheet in docs/assets/"
    css = "\n".join(f.read_text(encoding="utf-8") for f in css_files)

    # A declaration follows `{` or `;`, never `:` — the lookbehind is what keeps
    # pseudo-elements out of this, since `::-webkit-scrollbar-thumb:hover` reads
    # exactly like a property to a pattern that does not care what precedes it.
    prefixed = set(re.findall(r"(?<![:\w-])-webkit-([a-z-]+)\s*:", css))
    # Genuinely webkit-only surfaces with no standard counterpart to compare to.
    webkit_only = {"text-size-adjust", "font-smoothing", "tap-highlight-color",
                   "text-fill-color", "box-orient", "line-clamp",
                   "overflow-scrolling", "appearance"}
    orphaned = sorted(
        p for p in prefixed - webkit_only
        if not re.search(rf"(?<!-){re.escape(p)}\s*:", css)
    )
    assert not orphaned, (
        f"the built stylesheet declares -webkit-{orphaned} with no unprefixed "
        f"form. A minifier that rewrites properties against browser targets has "
        f"dropped the standard one; see the cssMinify note in astro.config.mjs.")


def test_every_language_span_declares_the_language_it_is_in():
    """WCAG 3.1.2, Language of Parts — the one accessibility item this page did
    not satisfy.

    Both languages sit in the markup at once and CSS hides one, so `<html lang>`
    alone is a claim about the whole document that is false for half of it. The
    practical impact is small, because the hidden half is `display: none` and a
    screen reader does not announce it — but "small" is the argument for fixing
    a one-attribute problem, not for keeping it. A Turkish sentence read out with
    English phonemes is the failure this criterion exists to name, and the moment
    a future edit hides a language by any means other than `display: none`, the
    claim becomes audible.

    The class already carries the answer; the attribute just says it in the
    language browsers and assistive tech actually read.
    """
    html = SITE.read_text(encoding="utf-8")
    for lang in ("tr", "en"):
        # The language class is always last in the attribute, so `class="hidden"`
        # cannot be mistaken for an English span.
        spans = re.findall(rf'<(\w+)([^>]*\bclass="(?:[^"]*\s)?{lang}")([^>]*)>', html)
        assert spans, f"the page carries no .{lang} spans at all — has the markup changed?"
        missing = [f"<{tag}{a}{b}>" for tag, a, b in spans
                   if f'lang="{lang}"' not in a + b]
        assert not missing, (
            f'{len(missing)} element(s) carry class="{lang}" without lang="{lang}": '
            f"{missing[:3]}")


def test_the_readmes_state_the_javascript_the_page_actually_ships():
    """Both READMEs described the page's script layer, and both described one
    that has not existed for several rounds: "0 KB of JavaScript (the page's
    only script is an ~18-line language toggle)".

    Two claims, and the interesting thing is that they failed in opposite
    directions. "0 KB" was true of the thing it was measuring — no JavaScript
    FILE is fetched, `script-src` carries hashes and nothing else — and false as
    a reader reads it, because five and a half kilobytes of script ship inside
    the HTML. "The only script is an ~18-line language toggle" was simply
    wrong: the toggle is the small half, beside a reveal observer, a section
    tracker, a phone menu and a back-to-top control.

    So the claim is restated as two things that are separately checkable — no
    downloadable script, and this much inline script — and both are checked
    here against the built page rather than against a memory of it. The size is
    given with a `~` and allowed a kilobyte of slack: the point is to catch a
    figure that has stopped being true, not to force an edit every time a line
    of script moves.
    """
    html = SITE.read_text(encoding="utf-8")

    external = re.findall(r"<script[^>]*\ssrc=", html)
    assert not external, f"the page fetches {len(external)} script file(s); both READMEs say it fetches none"

    # JSON-LD is data the browser never executes, so it is not part of the claim.
    executable = [
        body for tag, body in re.findall(
            r"(<script(?![^>]*\ssrc=)[^>]*>)([\s\S]*?)</script>", html)
        if "json" not in tag.lower()
    ]
    assert executable, "the page ships no inline script at all — restate the claim"
    actual_kb = sum(len(b.encode("utf-8")) for b in executable) / 1024

    for name in ("README.md", "README.tr.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        # Both decimal conventions: the Turkish README writes 5,5 and the
        # English one 5.5, and they are the same number.
        stated = re.search(r"~\s*(\d+[.,]\d+)\s*KB", text)
        assert stated, f"{name} no longer states the page's inline-script size"
        claimed = float(stated.group(1).replace(",", "."))
        assert abs(claimed - actual_kb) <= 1.0, (
            f"{name} says ~{claimed} KB of inline script; the built page ships "
            f"{actual_kb:.1f} KB. Restate it, or rebuild if the page is stale.")


def test_every_button_to_the_repository_is_drawn_the_same():
    """There are two "get the kit" buttons on the page — one under the headline
    and one in the closing band — and for three rounds only the first carried
    GitHub's mark.

    That is not a decoration bug. The two buttons are the same action, and a
    reader who has scrolled past the hero meets the second one cold: without
    the mark it is a light pill that says "get the kit" and does not say where
    from. The mark moved into `GitHubMark.astro` so there is one drawing of it,
    and this is the check that both places still use it — the failure it guards
    is a THIRD button being added later with the mark forgotten again, which is
    precisely how the second one lost it.
    """
    src = _site_ts()
    m = re.search(r"repo:\s*'([^']+)'", src)
    assert m, "web/src/data/site.ts declares no repo"
    repo = m.group(1)

    # The mark's own geometry, read from the component rather than copied here:
    # a test that carries its own copy of a 700-character path is a second place
    # for the path to live. `<svg>` alone would not do — every one of these
    # buttons ends in a chevron, which is also an svg.
    mark = (ROOT / "web" / "src" / "components" / "GitHubMark.astro").read_text(
        encoding="utf-8")
    d = re.search(r'<path d="([^"]{40,})"', mark)
    assert d, "GitHubMark.astro draws no path — has the component changed?"
    fragment = d.group(1)[:40]

    html = SITE.read_text(encoding="utf-8")
    buttons = re.findall(
        r'<a class="pill"[^>]*href="' + re.escape(repo) + r'"[^>]*>(.*?)</a>',
        html, re.S)
    assert len(buttons) >= 2, (
        f"docs/index.html has {len(buttons)} primary buttons pointing at the "
        f"repository; the page is built with one in the hero and one in the "
        f"closing band")
    bare = [i for i, b in enumerate(buttons) if fragment not in b]
    assert not bare, (
        f"button(s) {bare} link to the repository without GitHub's mark — use "
        f"<GitHubMark /> so both say where the download comes from")


def test_every_site_page_exists_and_shares_the_stylesheet():
    # One identity across five pages. A page that forgets the stylesheet renders
    # as unstyled HTML on a public domain — visible to everyone but the author,
    # who has it cached. The filename is content-hashed by the build, so this
    # matches the shape rather than a literal name, and then requires every page
    # to reference the SAME file.
    seen = set()
    for name, html in _pages().items():
        found = re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)
        assert found, f"{name} does not load a stylesheet"
        for href in found:
            assert (SITE_DIR / href).exists(), f"{name} links a missing stylesheet {href}"
            seen.add(href)
    assert len(seen) == 1, f"the pages load different stylesheets: {sorted(seen)}"
def test_no_built_page_uses_a_root_absolute_asset_path():
    # The build emits `/assets/…`, which resolves to the filesystem root under
    # file:// and renders the page unstyled when opened from disk. postbuild.mjs
    # rewrites those to relative; this is what notices if that step is dropped.
    for name, html in _pages().items():
        bad = re.findall(r'(?:href|src)="(/(?!/)[^"]*)"', html)
        assert not bad, f"{name} uses root-absolute asset path(s): {bad[:3]}"
def test_the_built_site_is_not_stale_against_its_public_files():
    """The classic committed-build-output failure: the source moves, the output
    does not, and the live site quietly serves last month's copy.

    A full rebuild inside pytest would need the Node toolchain, which this
    repository does not require. Instead this compares the files the build merely
    COPIES — `web/public/*` — against what sits in `docs/`. Those are also the
    files most likely to be edited in the wrong place, because `docs/PERFORMANCE.md`
    is what the READMEs link to and looks perfectly editable.
    """
    public = ROOT / "web" / "public"
    for src in public.iterdir():
        if not src.is_file():
            continue
        built = SITE_DIR / src.name
        assert built.exists(), (
            f"{src.name} is in web/public but not in docs/ — run `npm --prefix web "
            f"run build`")
        assert built.read_bytes() == src.read_bytes(), (
            f"docs/{src.name} differs from web/public/{src.name}. Edit the copy in "
            f"web/public/ and rebuild; docs/ is generated output.")
def test_the_built_site_carries_the_version_its_source_declares():
    # site.ts holds the version the pages render. If the build is stale, the
    # public site advertises an older release than the repository ships.
    source = (ROOT / "web" / "src" / "data" / "site.ts").read_text(encoding="utf-8")
    m = re.search(r"version:\s*'([^']+)'", source)
    assert m, "web/src/data/site.ts declares no version"
    assert m.group(1) == _cff()["version"], (
        f"site source says v{m.group(1)}, CITATION.cff says v{_cff()['version']}")
    # The version is no longer PRINTED on the page — it was one more line of
    # small text saying something a visitor has no opinion about — but the page
    # still states it, in the SoftwareApplication graph the head carries. That
    # is where a crawler and a citation tool look for it anyway, and it is
    # enough for the check this test exists to make: a `docs/` built before the
    # last version bump will not contain the current number in any form.
    for name, html in _pages().items():
        assert m.group(1) in html, (
            f"{name} states no version at all — the build is stale, or the "
            f"JSON-LD graph lost `softwareVersion`. Rebuild with "
            f"`npm --prefix web run build`.")
def test_the_built_site_states_the_current_hook_count():
    # site.ts is the source of truth and is checked above — but docs/ is what
    # visitors read, and it is committed build output that can sit stale behind
    # a corrected source. The wrong hook count was live on the site, not just in
    # the repository, so the assertion has to reach the rendered page.
    n = len(_registered_hooks())
    page = SITE.read_text(encoding="utf-8")
    assert re.search(rf"\b{n} hook\b", page) and re.search(rf"\b{n} hooks\b", page), (
        f"docs/index.html does not state {n} hooks in both languages — rebuild "
        f"with `npm --prefix web run build`")
    stale = re.search(r"\b(\d+) hooks\b", page)
    assert stale and int(stale.group(1)) == n, (
        f"docs/index.html still says {stale.group(1)} hooks")
def test_the_site_source_and_the_built_output_are_both_committed():
    # docs/ is build output that is deliberately committed — it is what makes the
    # deploy need no CI workflow. If the source disappeared, the site would be
    # unmaintainable; if the output did, the site would be gone.
    assert (ROOT / "web" / "package.json").exists(), "the site source is missing"
    assert (ROOT / "web" / "src" / "pages").is_dir()
    assert (SITE_DIR / "CNAME").exists(), "the built output lost its CNAME"
def test_every_internal_site_link_resolves():
    # The most visible possible defect on a live site, and the one nothing else
    # would catch until a visitor hits it.
    for name, html in _pages().items():
        for href in re.findall(r'href="(?!https?:|data:|#|mailto:)([^"]+)"', html):
            target = SITE_DIR / href.split("#")[0]
            assert target.exists(), f"{name} links {href}, which does not exist"
def test_every_page_carries_the_full_navigation():
    # The navigation is anchors now, so "carries the full navigation" means the
    # page offers every destination NAV declares AND that each one exists on it.
    # A dangling anchor is the one-page equivalent of a 404 and is quieter: the
    # click simply does nothing.
    nav = re.findall(r"href:\s*'(#[a-z-]+)'", (ROOT / "web" / "src" / "data" / "site.ts")
                     .read_text(encoding="utf-8"))
    assert len(nav) >= 4, f"NAV no longer declares anchors: {nav}"
    for name, html in _pages().items():
        for target in nav:
            assert f'href="{target}"' in html, f"{name} does not link {target}"
            assert f'id="{target[1:]}"' in html, f"{name} links {target} but has no such id"
        # Which item is current used to be a property of WHICH DOCUMENT this
        # was, so it could be asserted in the markup. On one page it is a
        # property of where the reader has scrolled to, and the script sets it.
        # What is still checkable — and is what would actually break — is the
        # hook the script needs: every nav link must carry the anchor it marks.
        for target in nav:
            assert f'data-anchor="{target}"' in html, (
                f"{name}: nav link {target} carries no data-anchor, so the "
                f"current-section marker can never find it")
def test_every_page_is_bilingual():
    # The kit's central claim is TR/EN parity. A page in one language only
    # contradicts it on the public site, which is where it is least excusable.
    for name, html in _pages().items():
        assert 'class="tr"' in html or "tr\"" in html, f"{name} has no Turkish content"
        assert 'class="en"' in html, f"{name} has no English content"
        assert 'id="lang"' in html, f"{name} has no language toggle"
def test_every_page_declares_its_own_canonical():
    # Five pages sharing one canonical would collapse the site to a single URL
    # in every index that reads it.
    seen = {}
    for name, html in _pages().items():
        m = re.search(r'rel="canonical"\s+href="([^"]+)"', html)
        assert m, f"{name} declares no canonical URL"
        assert m.group(1) not in seen, (
            f"{name} shares its canonical with {seen.get(m.group(1))}")
        seen[m.group(1)] = name
# `test_the_tools_page_lists_every_tool_in_the_repository` stood here and has
# been deleted with its subject. It read the tools chapter out of the built page
# and required the set of `<b>name.py</b>` in it to equal `scripts/` exactly —
# a good gate for a page that CLAIMED to list every tool. The site is an
# introduction now: it names no tool at all and links to the README instead, so
# there is no claim left to check and a test that passes vacuously is worse than
# no test, because it reads like coverage. Its import of `SCRIPTS` went with it.

def test_site_states_the_current_version():
    version = _cff()["version"]
    assert version in SITE.read_text(encoding="utf-8"), (
        f"the page does not show {version}; a stale version on the public page is "
        f"the claim readers check first")


# ---------- security headers ----------
def test_every_page_ships_a_content_security_policy():
    # GitHub Pages cannot set response headers, so the policy travels in a meta
    # tag injected by postbuild.mjs. A page that lost it is not visibly broken,
    # which is exactly why it needs a test.
    for name, html in _pages().items():
        directives = _csp(html)
        assert directives.get("default-src") == ["'none'"], (
            f"{name} does not start from default-src 'none'")
        for locked in ("base-uri", "form-action", "object-src", "connect-src"):
            assert directives.get(locked) == ["'none'"], f"{name} leaves {locked} open"
        assert "'unsafe-inline'" not in directives.get("style-src", []), (
            f"{name} allows inline styles — an inline style attribute crept back in")
def test_the_policy_hashes_exactly_the_scripts_on_the_page():
    """The load-bearing half of the CSP.

    A hash that does not match its script means the browser refuses to run it —
    on this site, the language toggle. Nothing else would notice: the page still
    renders, in whichever language the visitor did not choose.
    """
    import base64
    import hashlib

    for name, html in _pages().items():
        allowed = {t for t in _csp(html).get("script-src", []) if t.startswith("'sha256-")}
        actual = {
            "'sha256-" + base64.b64encode(
                hashlib.sha256(body.encode("utf-8")).digest()).decode() + "'"
            for body in _INLINE_SCRIPT.findall(html)
        }
        assert actual, f"{name} has no inline script — the toggle went missing"
        assert allowed == actual, (
            f"{name}: the CSP authorises {sorted(allowed - actual)} and omits "
            f"{sorted(actual - allowed)} — rebuild with `npm --prefix web run build`")
def test_no_built_page_carries_an_inline_style_attribute():
    # Under `style-src 'self'` a single style attribute is dropped by the
    # browser, so the element renders unstyled rather than erroring. Cheaper to
    # catch here than to notice in a screenshot.
    for name, html in _pages().items():
        found = re.findall(r'\sstyle="[^"]*"', html)
        assert not found, f"{name} uses inline style(s): {found[:3]}"
def test_every_page_points_at_the_share_card_on_its_own_domain():
    domain = (ROOT / "docs" / "CNAME").read_text(encoding="utf-8").strip()
    for name, html in _pages().items():
        m = re.search(r'property="og:image" content="([^"]+)"', html)
        assert m, f"{name} declares no og:image"
        assert m.group(1) == f"https://{domain}/og.png", (
            f"{name} points og:image at {m.group(1)}")
        assert 'property="og:image:alt"' in html, f"{name} gives the card no alt text"
def test_every_page_has_exactly_one_h1():
    # Both languages ship in the HTML, so each page carries one <h1> per
    # language and CSS hides one. Two <h1>s in the same language is the defect.
    for name, html in _pages().items():
        heads = re.findall(r'<h1[^>]*class="([^"]*)"', html)
        assert heads, f"{name} has no <h1>"
        for lang in ("tr", "en"):
            n = sum(1 for cls in heads if lang in cls.split())
            assert n == 1, f"{name} has {n} <h1> elements in {lang}, expected 1"
def test_every_page_offers_a_skip_link_to_its_main_landmark():
    # The first thing a keyboard user meets is this site's navigation, five
    # links deep, on every page.
    for name, html in _pages().items():
        assert 'class="skip" href="#main"' in html, f"{name} has no skip link"
        assert '<main id="main">' in html, f"{name} has no main landmark to skip to"
def test_the_built_site_states_the_same_test_count_as_its_source():
    """site.ts is the source; docs/ is generated output committed to the repo.
    Changing the number without rebuilding leaves the live site serving the old
    one — invisible in every other check here, because nothing else reads the
    built pages for it."""
    n = _site_number("tests")
    for html in _pages().values():
        if str(n) in html:
            return
    pytest.fail(
        f"no built page in docs/ states the current test count ({n}) — "
        f"run `npm --prefix web run build` after editing web/src/data/site.ts")

