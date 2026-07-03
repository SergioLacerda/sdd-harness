/* SDD Harness — announcement banner for MkDocs Material
 * Lives at  docs/app/sdd-banner.js  and is loaded from mkdocs.yml via
 *   extra_javascript: [app/sdd-banner.js]
 *
 * Self-contained: needs NO theme override / custom_dir. It injects a site-wide
 * CTA banner (styled by sdd-theme.css) that links to the static Selector. The
 * Selector build output sits as a sibling of the docs root (build/site/docs/
 * vs build/site/selector/), so the link is resolved relative to the docs
 * root and then up one level, so it works on every page and on the GitHub
 * Pages sub-path (…github.io/sdd-harness/docs/).
 *
 * Edit BANNER_TEXT / BANNER_CTA / SELECTOR_PATH below to taste.
 */
(function () {
  var lang = document.documentElement.lang || "en";
  var BANNER_STRINGS = {
    en: {
      text: "Explore the mandates and directives governed in the interactive Selector.",
      cta:  "Explore mandates and directives →",
    },
    pt: {
      text: "Explore os mandatos e diretrizes governados no Seletor interativo.",
      cta:  "Explorar mandatos e diretrizes →",
    },
  };
  var _s = lang.startsWith("pt") ? BANNER_STRINGS.pt : BANNER_STRINGS.en;
  var BANNER_TEXT = _s.text;
  var BANNER_CTA  = _s.cta;
  var SELECTOR_PATH = "selector/" + (lang.startsWith("pt") ? "?lang=pt" : "");

  function rootHref() {
    // Material's logo/home link points to the site root, relative to this page.
    var logo = document.querySelector(".md-header__button.md-logo")
            || document.querySelector("a.md-logo")
            || document.querySelector('[data-md-component="logo"]');
    var href = logo && logo.getAttribute("href");
    if (!href) {
      var base = document.querySelector("base");
      href = (base && base.getAttribute("href")) || "./";
    }
    if (href.charAt(href.length - 1) !== "/") href += "/";
    return href;
  }

  function build() {
    if (document.querySelector(".sdd-banner")) return;     // avoid duplicates
    if (!document.body) return;
    var url = rootHref() + "../" + SELECTOR_PATH;
    var bar = document.createElement("div");
    bar.className = "sdd-banner";
    var inner = document.createElement("div");
    inner.className = "sdd-banner-inner";
    var textSpan = document.createElement("span");
    textSpan.className = "sdd-banner-text";
    var a = document.createElement("a");
    a.className = "sdd-banner-cta";
    inner.append(textSpan, a);
    bar.append(inner);
    textSpan.textContent = BANNER_TEXT;
    a.textContent = BANNER_CTA;
    a.setAttribute("href", url);
    // Open in a new tab — sidesteps Material's navigation.instant (which would
    // otherwise try to XHR-swap this standalone page into the docs shell).
    a.setAttribute("target", "_blank");
    a.setAttribute("rel", "noopener");
    document.body.insertBefore(bar, document.body.firstChild);
  }

  // Material "instant loading" swaps the DOM via document$ — rebuild each time.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(build);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
