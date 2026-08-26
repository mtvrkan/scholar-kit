// @ts-check
import { defineConfig } from 'astro/config';

// Build output goes straight into ../docs, which GitHub Pages serves from the
// main branch. That is why the built site is committed: it keeps the deploy free
// of a CI workflow — one Pages setting and one DNS record, nothing else.
//
// `format: 'file'` emits komutlar.html rather than komutlar/index.html. Chosen
// deliberately: relative links then behave identically over http and over
// file://, so `docs/index.html` opened straight from disk IS the site. Directory
// URLs would read marginally cleaner and break local preview — and being able to
// check the thing without a server is worth more than the slash.
export default defineConfig({
  site: 'https://scholar.mtvrkan.com',
  outDir: '../docs',
  // `inlineStylesheets: 'never'` is load-bearing twice over. It keeps every page
  // pointing at one hashed stylesheet — which is what a governance test asserts,
  // since a page that silently lost the stylesheet renders as raw HTML on a
  // public domain. And it keeps `style-src 'self'` honest: an inlined <style>
  // block would force 'unsafe-inline' back into the injected CSP for every page.
  build: { format: 'file', assets: 'assets', inlineStylesheets: 'never' },
  compressHTML: true,
  devToolbar: { enabled: false },
  // esbuild minifies the CSS, not Lightning CSS, and this is load-bearing
  // rather than a preference.
  //
  // Astro 7 switched the default, and Lightning CSS rewrites properties against
  // its browser targets rather than only compressing them. On the defaults here
  // it replaced every `backdrop-filter` with `-webkit-backdrop-filter` ALONE —
  // dropping the standard property. Current Chrome no longer answers to the
  // webkit alias (`CSS.supports('-webkit-backdrop-filter', 'blur(2px)')` is
  // false), so the declaration resolved to nothing and the blur disappeared
  // from every glass surface on the page: the masthead pane, the lit nav item,
  // the figure strip. The stylesheet's own token block names blur as one of the
  // four things that make a pane read as glass rather than as a tinted box, so
  // this was the design losing a layer — with a green build, a green suite and
  // no visible error anywhere. `test_the_built_stylesheet_keeps_the_standard_
  // property_beside_every_prefixed_one` is the guard; this line is the fix.
  vite: { build: { cssMinify: 'esbuild' } },
  // No sitemap integration. It emits `sitemap-index.xml` pointing at
  // `sitemap-0.xml`, which is the right shape for a site with enough URLs to
  // need paging and a needless indirection for one that has a single page. The
  // sitemap is `public/sitemap.xml`: one URL, no lastmod — a date that is
  // rewritten on every build is diff noise, and a date that is not rewritten is
  // a lie. Crawlers look for /sitemap.xml first, and robots.txt names it.
});
