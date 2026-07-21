/* Plumbline — minimal progressive enhancement. No dependencies, no network.
   Everything here is optional: the site is fully usable without JS. */
(function () {
  "use strict";
  var KEY = "plumbline-theme";
  var root = document.documentElement;

  function currentTheme() {
    var attr = root.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function syncToggle(btn) {
    var isDark = currentTheme() === "dark";
    btn.setAttribute("aria-pressed", String(isDark));
    var label = isDark ? "Switch to light theme" : "Switch to dark theme";
    btn.setAttribute("aria-label", label);
    var sr = btn.querySelector(".sr-only");
    if (sr) sr.textContent = label;
  }

  // Theme toggle.
  var toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    syncToggle(toggle);
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      syncToggle(toggle);
    });
  }

  // Scroll-reveal. Content is NEVER left hidden: three failsafes (no IO, thrown
  // error, and a hard 2.5s timeout) all reveal everything.
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var reveals = document.querySelectorAll("[data-reveal]");
  function revealAll() {
    for (var i = 0; i < reveals.length; i++) reveals[i].classList.add("is-in");
  }
  if (reveals.length && !reduce) {
    if (!("IntersectionObserver" in window)) {
      revealAll();
    } else {
      try {
        var io = new IntersectionObserver(
          function (entries) {
            entries.forEach(function (e) {
              if (e.isIntersecting) {
                e.target.classList.add("is-in");
                io.unobserve(e.target);
              }
            });
          },
          { rootMargin: "0px 0px -10% 0px", threshold: 0.12 }
        );
        for (var j = 0; j < reveals.length; j++) io.observe(reveals[j]);
        setTimeout(revealAll, 2500);
      } catch (e) {
        revealAll();
      }
    }
  } else {
    revealAll();
  }

  // Deepen the sticky-header shadow once the page is scrolled (shadow only — no CLS).
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-pinned", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // Jump-to-state: enhance the hero form to navigate straight to a state hub.
  var jump = document.querySelector("select[data-jump]");
  if (jump) {
    var form = jump.closest("form");
    if (form) {
      form.addEventListener("submit", function (e) {
        var opt = jump.options[jump.selectedIndex];
        var url = opt && opt.getAttribute("data-url");
        if (url) {
          e.preventDefault();
          window.location.href = url;
        }
      });
    }
  }
})();
