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
    var label = currentTheme() === "dark" ? "Switch to light theme" : "Switch to dark theme";
    btn.setAttribute("aria-label", label);
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
    // The OS theme can change while the page is open; keep the label truthful.
    var mq = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
    if (mq && mq.addEventListener) {
      mq.addEventListener("change", function () { syncToggle(toggle); });
    }
  }

  // ---------------------------------------------------------------- countdowns
  // This HTML is a static build that may be days old, so every relative phrase
  // ("in 2 days", "Today") is recomputed against the reader's own clock. The
  // server-rendered text is the no-JS fallback and is never removed, only replaced.
  var MS_DAY = 86400000;
  function daysUntil(iso) {
    var parts = iso.split("-");
    if (parts.length !== 3) return null;
    // Compare calendar days in the reader's local zone, not elapsed hours.
    var target = new Date(+parts[0], +parts[1] - 1, +parts[2]);
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return Math.round((target - today) / MS_DAY);
  }
  function phrase(n) {
    if (n === 0) return "Today";
    if (n === 1) return "Tomorrow";
    if (n > 1) return "in " + n + " days";
    if (n === -1) return "Yesterday";
    return Math.abs(n) + " days ago";
  }
  function refreshCountdowns() {
    var nodes = document.querySelectorAll("[data-countdown]");
    for (var i = 0; i < nodes.length; i++) {
      var n = daysUntil(nodes[i].getAttribute("data-countdown"));
      if (n === null) continue;
      // Compact format (state tiles) keeps the absolute date; only the urgency
      // bar and the accessible name need refreshing there.
      if (nodes[i].getAttribute("data-countdown-format") === "compact") continue;
      nodes[i].textContent = phrase(n);
    }
    var chips = document.querySelectorAll("[data-deadline]");
    for (var j = 0; j < chips.length; j++) {
      var chip = chips[j];
      var d = daysUntil(chip.getAttribute("data-deadline"));
      if (d === null) continue;
      var opens = chip.hasAttribute("data-opens");
      var endAttr = chip.getAttribute("data-window-end");
      var end = endAttr ? daysUntil(endAttr) : null;
      var state = "";
      chip.classList.remove(
        "deadline-chip--today", "deadline-chip--urgent",
        "deadline-chip--closed", "deadline-chip--open"
      );
      if (opens) {
        if (d > 0) { state = "Opens"; }
        else if (end === null || end >= 0) { chip.classList.add("deadline-chip--open"); state = "Open now"; }
        else { chip.classList.add("deadline-chip--closed"); state = "Closed"; }
      } else if (d === 0) {
        chip.classList.add("deadline-chip--today"); state = "Today";
      } else if (d > 0 && d <= 7) {
        chip.classList.add("deadline-chip--urgent");
        state = "in " + d + " day" + (d === 1 ? "" : "s");
      } else if (d < 0) {
        chip.classList.add("deadline-chip--closed"); state = "Closed";
      }
      var slot = chip.querySelector(".deadline-chip__state");
      if (!slot && state) {
        slot = document.createElement("span");
        slot.className = "deadline-chip__state";
        chip.appendChild(slot);
      }
      if (slot) slot.textContent = state;
    }
  }
  try { refreshCountdowns(); } catch (e) {}

  // ------------------------------------------------------------- scroll reveal
  // The class that HIDES content is added here, not by the pre-paint script in
  // <head>. If this file fails to load, `reveal-on` is never set, the hiding
  // rules never match, and every page renders in full. Content can only be
  // hidden by the same file that is able to show it again.
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var reveals = document.querySelectorAll("[data-reveal]");
  function revealAll() {
    for (var i = 0; i < reveals.length; i++) reveals[i].classList.add("is-in");
  }
  var nav = (window.performance && performance.getEntriesByType)
    ? performance.getEntriesByType("navigation")[0] : null;
  var restored = nav && nav.type === "back_forward";

  if (reveals.length && !reduce && !restored) {
    root.classList.add("reveal-on");
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
          // threshold 0 + rootMargin: a block taller than the viewport can never
          // reach a fractional threshold and would rely on the timer alone.
          { rootMargin: "0px 0px -10% 0px", threshold: 0 }
        );
        for (var j2 = 0; j2 < reveals.length; j2++) io.observe(reveals[j2]);
        setTimeout(revealAll, 2500);
      } catch (e) {
        revealAll();
      }
    }
  } else {
    revealAll();
  }
  // Printing paginates content the IntersectionObserver never saw, and a restored
  // page should not re-play an animation over text the reader was mid-way through.
  window.addEventListener("beforeprint", revealAll);
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) revealAll();
    var sel = document.querySelector("select[data-jump]");
    if (sel) sel.selectedIndex = 0;
  });

  // Deepen the sticky-header shadow once the page is scrolled (shadow only — no CLS).
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-pinned", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    // Anchor jumps need the real header height, which changes as the nav wraps.
    var syncHeaderHeight = function () {
      root.style.setProperty("--header-h", header.offsetHeight + "px");
    };
    syncHeaderHeight();
    window.addEventListener("resize", syncHeaderHeight, { passive: true });
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
