/* SDD Harness — announcement banner for MkDocs Material
 * Lives at  docs/app/sdd-banner.js  and is loaded from mkdocs.yml via
 *   extra_javascript: [app/sdd-banner.js]
 *
 * Self-contained: needs NO theme override / custom_dir. It injects a site-wide
 * CTA banner (styled by sdd-theme.css) that links to the static Selector. The
 * link is resolved relative to the site root, so it works on every page and on
 * the GitHub Pages sub-path (…github.io/sdd-harness/).
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
    var url = rootHref() + SELECTOR_PATH;
    var bar = document.createElement("div");
    bar.className = "sdd-banner";
    bar.innerHTML =
      '<div class="sdd-banner-inner">' +
        '<span class="sdd-banner-text"></span>' +
        '<a class="sdd-banner-cta"></a>' +
      "</div>";
    bar.querySelector(".sdd-banner-text").textContent = BANNER_TEXT;
    var a = bar.querySelector(".sdd-banner-cta");
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
