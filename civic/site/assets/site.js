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
