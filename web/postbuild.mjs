/**
 * Post-build: clean up residue, relativise asset paths, inject the CSP.
 *
 * The output directory here is not a throwaway `dist/`: it is `../docs`, which
 * is committed and served. Anything left behind ends up in the repository and on
 * the public site, so all three steps are part of the build rather than a nicety.
 *
 * 1. Stray build artefacts. Astro 5's content layer emitted `content-assets.mjs`
 *    / `content-modules.mjs` even for a project that declares no content
 *    collections, and the sitemap integration left an index pointing at a paged
 *    sitemap. Neither happens any more — Astro 7 emits neither, and the sitemap
 *    integration has been uninstalled — so this sweep now removes nothing on
 *    every build. It is kept rather than deleted because the cost is four
 *    `access()` calls and the failure it guards against is silent: a file
 *    nobody references, committed into `docs/` and served on a public domain.
 *
 * 2. Astro emits root-absolute asset paths (`/assets/x.css`). Those resolve to
 *    the filesystem root under `file://`, so opening `docs/index.html` straight
 *    from disk would render unstyled. Every page in this site sits at the same
 *    depth, so a root-absolute path and a relative one address the same file —
 *    rewriting to relative costs nothing on the server and makes local preview
 *    work. That preview is the reason `format: 'file'` was chosen too.
 *
 * 3. GitHub Pages serves static files and cannot set response headers, so the
 *    Content-Security-Policy has to travel in a <meta> tag. It is injected HERE
 *    rather than written in the layout because the policy names the SHA-256 of
 *    every inline script on the page: computing it after the page exists is the
 *    only way the hash cannot drift from the script it authorises. Change the
 *    language toggle and the next build re-hashes it; hand-edit the built page
 *    and the browser refuses to run the script, which is the correct outcome.
 *
 *    Two limits worth stating rather than pretending away. A <meta> policy
 *    cannot express `frame-ancestors`, `report-uri` or `sandbox` — those are
 *    header-only, so clickjacking protection is not available on Pages at all.
 *    And a CSP delivered in the document is a defence against injected content,
 *    not against a compromised host: whoever can rewrite the HTML can rewrite
 *    the policy with it.
 *
 * 4. Comments come out of the shipped bytes. The sources here are written with
 *    their reasoning beside them and that is deliberate; what is not deliberate
 *    is that reasoning arriving in View Source, where it is a note to an author
 *    read by an audience it was never addressed to. The bundled stylesheet was
 *    already clean because the CSS minifier drops comments; the pages and their
 *    inline scripts were not, and shipped eighteen paragraphs of design notes.
 *
 *    Doing it here rather than by emptying the sources is what makes it hold:
 *    a one-off deletion is undone by the next edit that explains itself, and
 *    every edit in this repository explains itself.
 */
import { createHash } from 'node:crypto';
import { rm, access, readdir, readFile, writeFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { transform } from 'esbuild';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'docs');
const RESIDUE = [
  // Left behind by the sitemap integration this build no longer uses.
  'sitemap-index.xml',
  'sitemap-0.xml','content-assets.mjs', 'content-modules.mjs'];

// `default-src 'none'` is the whole point: everything the page may load is then
// an explicit exception. img-src carries `data:` for the inline SVG favicon.
//
// Not one directive names a host. `media-src` used to name a CloudFront
// distribution for the backdrop footage, which made it the single outbound
// request the site issued and cost the "zero external requests" claim its
// unqualified form. The backdrop is gone (see Base.astro), so the directive is
// back to 'none' along with everything else the page never loads — and the
// claim is once again the simple one it reads best as.
const DIRECTIVES = [
  "default-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "img-src 'self' data:",
  "style-src 'self'",
  "font-src 'self'",
  "media-src 'none'",
  "connect-src 'none'",
  "frame-src 'none'",
  // Nothing here is meant to be framed. Without this a copy of the page can be
  // put inside someone else's chrome and presented as theirs, and on a site
  // whose whole argument is provenance that is the one embedding that costs
  // something. `X-Frame-Options` is a header and Pages sends no custom headers,
  // so the CSP form is the only one available here — and it is the stronger of
  // the two anyway.
  "frame-ancestors 'none'",
  "object-src 'none'",
  "manifest-src 'none'",
];

let removed = 0;
for (const name of RESIDUE) {
  const path = join(OUT, name);
  try {
    await access(path);
    await rm(path);
    removed++;
  } catch {
    // Absent is the desired state; a future Astro version may stop emitting it.
  }
}

// Only href/src attributes, and only a single leading slash — this must not
// touch protocol-relative URLs (`//host/…`) or anything inside page text.
const ABSOLUTE = /((?:href|src)=")\/(?!\/)/g;

// Inline scripts only: a `src=` tag carries no body to hash, and matching one
// would silently produce the hash of an empty string.
const INLINE_SCRIPT = /<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g;

// Comment removal. Two languages in one file, so the document is walked in
// segments rather than swept with one expression: markup outside <script> and
// <style> loses its `<!-- -->` blocks, and a script body is handed to esbuild.
//
// esbuild rather than a regex, and this is the whole reason the step is safe.
// `//` appears inside every absolute URL the page holds and `/* */` appears
// inside at least one string literal here; a pattern that cannot tell a comment
// from a string turns `'https://scholar.mtvrkan.com'` into `'https:` and the
// page stops running — silently, because the CSP hash is computed after and
// would faithfully authorise the broken script. esbuild parses, so it knows the
// difference. `minify` is off deliberately: the goal is to remove the notes,
// not to make the one script on this page unreadable to a reader who looks.
const MARKUP_BLOCK = /<(script|style)\b([^>]*)>([\s\S]*?)<\/\1>/gi;
const HTML_COMMENT = /<!--[\s\S]*?-->/g;
// JSON-LD is data. Handing it to a JavaScript parser would either fail or
// reformat it into something that is no longer the graph the page declared.
const JSON_SCRIPT = /type\s*=\s*(['"]?)[^'">\s]*json[^'">\s]*\1/i;

async function decomment(html) {
  let out = '';
  let cursor = 0;
  let removed = 0;
  const count = (s) => s.replace(HTML_COMMENT, () => { removed++; return ''; });

  for (const m of html.matchAll(MARKUP_BLOCK)) {
    out += count(html.slice(cursor, m.index));
    const [whole, tag, attrs, body] = m;
    if (tag.toLowerCase() === 'script' && body.trim() && !JSON_SCRIPT.test(attrs)) {
      const before = body;
      const { code } = await transform(body, { loader: 'js', legalComments: 'none' });
      if (code !== before) removed++;
      out += `<script${attrs}>${code}</script>`;
    } else {
      out += whole;
    }
    cursor = m.index + whole.length;
  }
  return { html: out + count(html.slice(cursor)), removed };
}

// The same root-absolute problem as the pages, one directory deeper. The
// stylesheet is emitted to `docs/assets/` and its @font-face rules point at
// `/fonts/…` — root-absolute because that is the only form Vite leaves alone
// for public-directory assets instead of trying to resolve it beside the source
// file. Under file:// that resolves to the filesystem root and the fonts
// silently fall back to the system stack, which is exactly the kind of failure
// only the author never sees. From `docs/assets/x.css`, `../fonts/…` is the
// same file on the server and the right one on disk.
const CSS_ABSOLUTE = /(url\((['"]?))\/(?!\/)/g;
let fontPaths = 0;
const assetsDir = join(OUT, 'assets');
try {
  for (const name of await readdir(assetsDir)) {
    if (!name.endsWith('.css')) continue;
    const path = join(assetsDir, name);
    const original = await readFile(path, 'utf8');
    const css = original.replace(CSS_ABSOLUTE, '$1../');
    if (css !== original) {
      await writeFile(path, css, 'utf8');
      fontPaths++;
    }
  }
} catch {
  // No assets/ directory means no bundled stylesheet to fix, which the page
  // tests catch on their own terms.
}

let rewritten = 0;
let policed = 0;
let hashed = 0;
let decommented = 0;

for (const name of await readdir(OUT)) {
  if (!name.endsWith('.html')) continue;
  const path = join(OUT, name);
  const original = await readFile(path, 'utf8');

  let html = original.replace(ABSOLUTE, '$1');
  if (html !== original) rewritten++;

  // Before the hashing, necessarily: the policy names the SHA-256 of each
  // script as shipped, so anything that edits a script has to happen first or
  // the browser refuses to run the very file this step just cleaned.
  const stripped = await decomment(html);
  html = stripped.html;
  decommented += stripped.removed;

  // JSON-LD blocks are data, not code — but browsers enforce script-src on any
  // inline <script> regardless of type, so they are hashed alongside the rest.
  const hashes = [...html.matchAll(INLINE_SCRIPT)].map(
    (m) => `'sha256-${createHash('sha256').update(m[1], 'utf8').digest('base64')}'`);
  hashed += hashes.length;

  const policy = [...DIRECTIVES, `script-src ${hashes.join(' ') || "'none'"}`].join('; ');
  const meta = `<meta http-equiv="Content-Security-Policy" content="${policy}">`;

  if (html.includes('http-equiv="Content-Security-Policy"')) {
    throw new Error(`${name} already carries a CSP — the source should not set one`);
  }
  // Immediately after <meta charset>, so the policy is in force before anything
  // else in <head> is parsed.
  const anchor = html.match(/<meta charset="[^"]*">/i);
  if (!anchor) throw new Error(`${name} has no <meta charset> to anchor the CSP to`);
  html = html.replace(anchor[0], anchor[0] + meta);
  policed++;

  if (html !== original) await writeFile(path, html, 'utf8');
}

console.log(
  `postbuild: removed ${removed} unreferenced artefact(s), ` +
  `relativised asset paths in ${rewritten} page(s) and ${fontPaths} stylesheet(s), ` +
  `stripped ${decommented} comment block(s) from the shipped bytes, ` +
  `injected CSP over ${hashed} inline script(s) in ${policed} page(s)`);
