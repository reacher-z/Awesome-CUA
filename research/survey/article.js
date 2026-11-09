(() => {
  "use strict";

  const contents = document.getElementById("article-contents");
  const desktop = window.matchMedia("(min-width: 1080px)");
  if (contents) {
    // The HTML is closed by default; only a desktop reader starts expanded.
    contents.open = desktop.matches;
    const onBreakpoint = (event) => { contents.open = event.matches; };
    if (desktop.addEventListener) desktop.addEventListener("change", onBreakpoint);
    else desktop.addListener(onBreakpoint);
  }

  const tocLinks = Array.from(document.querySelectorAll('#article-toc-nav a[href^="#"]'));
  const linkTargets = tocLinks.map((link) => {
    let id;
    try { id = decodeURIComponent(link.hash.slice(1)); } catch { return null; }
    const element = document.getElementById(id);
    return element ? { link, element } : null;
  }).filter(Boolean);

  let scheduled = false;
  const markSection = () => {
    scheduled = false;
    if (!linkTargets.length) return;
    let active = null;
    for (const item of linkTargets) {
      if (item.element.getBoundingClientRect().top <= 150) active = item;
    }
    for (const item of linkTargets) {
      if (item === active) item.link.setAttribute("aria-current", "location");
      else item.link.removeAttribute("aria-current");
    }
  };
  const scheduleSectionMark = () => {
    if (!scheduled) {
      scheduled = true;
      window.requestAnimationFrame(markSection);
    }
  };
  window.addEventListener("scroll", scheduleSectionMark, { passive: true });
  window.addEventListener("resize", scheduleSectionMark, { passive: true });
  markSection();

  for (const link of tocLinks) {
    link.addEventListener("click", () => {
      if (contents && !desktop.matches) contents.open = false;
    });
  }

  // Make genuinely overflowing tables keyboard-scrollable, without changing text.
  const tableScrollers = Array.from(document.querySelectorAll(".table-scroll, .table-wrap, .paper table, .paper figure > [data-figure]"))
    .filter((element) => element.tagName !== "TABLE" || !element.parentElement.matches(".table-scroll, .table-wrap"));
  const updateTableAccess = () => {
    for (const element of tableScrollers) {
      if (element.scrollWidth > element.clientWidth + 2) {
        element.tabIndex = 0;
        if (element.tagName !== "TABLE") {
          element.setAttribute("role", "region");
          element.setAttribute("aria-label", element.hasAttribute("data-figure")
            ? "Inventory figure. Scroll horizontally to read both panels."
            : "Comparison table. Scroll horizontally to read all columns.");
        }
      } else {
        element.removeAttribute("tabindex");
        if (element.tagName !== "TABLE") {
          element.removeAttribute("role");
          element.removeAttribute("aria-label");
        }
      }
    }
  };
  updateTableAccess();
  if ("ResizeObserver" in window) {
    const observer = new ResizeObserver(updateTableAccess);
    for (const element of tableScrollers) observer.observe(element);
  } else {
    window.addEventListener("resize", updateTableAccess, { passive: true });
  }

  const referenceList = document.getElementById("reference-list");
  const filter = document.getElementById("reference-filter");
  const query = document.getElementById("reference-query");
  const status = document.getElementById("reference-filter-status");
  const empty = document.getElementById("reference-empty");
  const references = referenceList
    ? Array.from(referenceList.querySelectorAll(":scope > ol > li, :scope > ul > li"))
    : [];

  if (filter && query && status && references.length) {
    const normalize = (value) => value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("en");
    const entries = references.map((element, index) => {
      // Keep original citation numbers even when intervening items are hidden.
      if (element.parentElement.tagName === "OL" && !element.hasAttribute("value")) {
        element.value = index + Number(element.parentElement.getAttribute("start") || 1);
      }
      return { element, searchText: normalize(element.textContent || "") };
    });
    const applyFilter = () => {
      const terms = normalize(query.value.trim()).split(/\s+/).filter(Boolean);
      let visible = 0;
      for (const { element, searchText } of entries) {
        const matches = terms.every((term) => searchText.includes(term));
        element.hidden = !matches;
        if (matches) visible += 1;
      }
      status.textContent = terms.length
        ? `${visible} of ${entries.length} references shown.`
        : `All ${entries.length} references shown.`;
      if (empty) empty.hidden = visible !== 0;
    };
    const revealHashReference = () => {
      let id;
      try { id = decodeURIComponent(window.location.hash.slice(1)); } catch { return; }
      const target = document.getElementById(id);
      if (!target || !referenceList.contains(target)) return;
      const entry = target.closest("li");
      if (entry && entry.hidden) {
        query.value = "";
        applyFilter();
        target.scrollIntoView({ block: "start", behavior: "auto" });
      }
    };
    filter.hidden = false;
    filter.addEventListener("submit", (event) => event.preventDefault());
    filter.addEventListener("reset", () => {
      query.value = "";
      applyFilter();
    });
    query.addEventListener("input", applyFilter);
    window.addEventListener("hashchange", revealHashReference);
    // Also handle clicking the same reference hash after filtering it out.
    document.addEventListener("click", (event) => {
      const link = event.target instanceof Element ? event.target.closest('a[href^="#"]') : null;
      if (!link) return;
      let id;
      try { id = decodeURIComponent(link.hash.slice(1)); } catch { return; }
      const target = document.getElementById(id);
      if (target && referenceList.contains(target)) {
        query.value = "";
        applyFilter();
      }
    });
    applyFilter();
    revealHashReference();
  }
})();
