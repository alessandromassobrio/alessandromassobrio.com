// -----------------------------
// Entry point
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadWorksPage();
});

// -----------------------------
// Load works page
// -----------------------------
function loadWorksPage() {
  fetch("/works/works.json")
    .then(res => res.json())
    .then(works => {
      // Ordina per anno discendente
      works.sort((a, b) => b.year - a.year);

      renderWorksList(works);

      const params = new URLSearchParams(window.location.search);
      const slug = params.get("work");

      const initialWork =
        works.find(w => w.slug === slug) || works[0];

      setActiveWork(initialWork, works);
    })
    .catch(err => console.error(err));
}

// -----------------------------
// Render works list (left column + select)
// -----------------------------
function renderWorksList(works) {
  const ul = document.querySelector(".works-list");
  const select = document.getElementById("works-dropdown");

  ul.innerHTML = "";
  select.innerHTML = "";

  works.forEach((work, index) => {
    /* ---------- LISTA ---------- */
    const li = document.createElement("li");
    li.textContent = `${work.title} (${work.year})`;
    li.dataset.slug = work.slug;

    li.addEventListener("click", () => {
      setActiveWork(work, works);
      // Imposta parametro nella query
      const url = new URL(window.location);
      url.searchParams.set("work", work.slug);
      history.pushState({}, "", url);
      select.value = work.slug;
    });

    ul.appendChild(li);

    /* ---------- SELECT ---------- */
    const option = document.createElement("option");
    option.value = work.slug;
    option.textContent = `${work.title} (${work.year})`;
    if (index === 0) option.selected = true;
    select.appendChild(option);
  });

  /* change via select */
  select.addEventListener("change", e => {
    const selected = works.find(w => w.slug === e.target.value);
    if (selected) {
      setActiveWork(selected, works);
      const url = new URL(window.location);
      url.searchParams.set("work", selected.slug);
      history.pushState({}, "", url);
    }
  });
}

// -----------------------------
// Set active work
// -----------------------------
function setActiveWork(work, works) {
  document.querySelectorAll(".works-list li").forEach(li => {
    li.classList.toggle(
      "active",
      li.dataset.slug === work.slug
    );
  });

  const select = document.getElementById("works-dropdown");
  if (select) select.value = work.slug;

  loadWorkDetail(work);
}

// -----------------------------
// Load single work detail (right column)
// -----------------------------
function loadWorkDetail(work) {
  fetch(`/data/${work.id}.md`)
    .then(res => res.text())
    .then(text => {
      const { meta, content } = parseFrontMatter(text);

      renderTabs(content, meta, work.id);

      initTabs();

      setPageTitle(meta.title);
    })
    .catch(() => {
      document.querySelector(".work-detail").innerHTML =
        "<p>Work not found.</p>";
    });
}

// -----------------------------
// Parse YAML front-matter
// -----------------------------
function parseFrontMatter(text) {
  const match = text.match(/^---([\s\S]*?)---([\s\S]*)$/);
  if (!match) return { meta: {}, content: text };

  const meta = {};
  match[1].trim().split("\n").forEach(line => {
    const [key, ...value] = line.split(":");
    meta[key.trim()] = value.join(":").trim();
  });

  return { meta, content: match[2].trim() };
}

// -----------------------------
// Render tabs + meta
// -----------------------------
function renderTabs(content, meta, workId) {
  const detail = document.querySelector(".work-detail");

  // cleanup
  detail.querySelectorAll(".tabs, .tab-content, .back-link").forEach(el => el.remove());

  function splitSections(markdown) {
    const regex = /^##\s+(.+)$/gm;
    const matches = [...markdown.matchAll(regex)];

    if (!matches.length) {
      return [{ title: "Info", body: markdown }];
    }

    return matches.map((match, i) => {
      const start = match.index + match[0].length;
      const end = matches[i + 1]?.index ?? markdown.length;

      return {
        title: match[1].trim(),
        body: markdown.slice(start, end).trim()
      };
    });
  }

  const tabs = document.createElement("div");
  tabs.className = "tabs";
  detail.appendChild(tabs);

  const select = document.getElementById("tabs-dropdown");
  select.innerHTML = "";

  const sections = splitSections(content);

  sections.forEach((section, idx) => {
    const id = section.title.toLowerCase().replace(/[^\w]+/g, "-");

    // ---------- Button ----------
    const btn = document.createElement("button");
    btn.dataset.tab = id;
    btn.textContent = section.title;
    if (idx === 0) btn.classList.add("active");
    tabs.appendChild(btn);

    // ---------- Tab content ----------
    const tab = document.createElement("div");
    tab.id = `tab-${id}`;
    tab.className = "tab-content";
    if (idx === 0) tab.classList.add("active");

    // Inserisco meta solo nella prima tab "Info"
    if (idx === 0) {
      const metaItems = [
        { label: "Year", value: meta.year },
        { label: "Duration", value: meta.duration },
        { label: "Pages", value: formatScorePages(meta) },
        { label: "Category", value: meta.category },
        { label: "Instrumentation", value: meta.instrumentation },
        { label: "Cycle", value: meta.cycle }
      ]
        .filter(item => item.value && item.value.trim() !== "")
        .map(
          item => `<li><strong>${item.label}:</strong> ${item.value}</li>`
        )
        .join("");

      tab.innerHTML = `
        <div class="work-info-meta">
          ${meta.title ? `<h1>${meta.title}</h1>` : ""}
          ${metaItems ? `<ul>${metaItems}</ul>` : ""}
        </div>
        ${marked.parse(section.body)}
        ${renderScoreOverview(meta)}
      `;
    } else {
      tab.innerHTML = marked.parse(section.body);
    }

    detail.appendChild(tab);

    // ---------- Select ----------
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = section.title;
    if (idx === 0) opt.selected = true;
    select.appendChild(opt);
  });

  // -------- Request score tab --------
  const requestId = "request-score";

  const reqBtn = document.createElement("button");
  reqBtn.dataset.tab = requestId;
  reqBtn.textContent = "Request score";
  tabs.appendChild(reqBtn);

  const reqTab = document.createElement("div");
  reqTab.id = `tab-${requestId}`;
  reqTab.className = "tab-content";
  reqTab.innerHTML = `
    <p>
      <a href="mailto:info@alessandromassobrio.com
        ?subject=${encodeURIComponent(`Request score for ${meta.title}`)}
        &body=${encodeURIComponent(
          `I would like to request a copy of the score of "${meta.title}" for the following purpose/use:\n\n`
        )}">
        Request a copy of the score
      </a>
    </p>
  `;
  detail.appendChild(reqTab);

  const reqOpt = document.createElement("option");
  reqOpt.value = requestId;
  reqOpt.textContent = "Request score";
  select.appendChild(reqOpt);

  youtubefacades(detail);
}

// -----------------------------
// Score overview (tutte le pagine della partitura in un'unica immagine)
// -----------------------------
function formatScorePages(meta) {
  // "17" oppure, con più partiture, "39 | 20" + etichette → "Version 1 (2019): 39 · Rev. mdi (2024): 20"
  if (!meta.score_pages) return "";
  const counts = meta.score_pages.split("|").map(s => s.trim()).filter(Boolean);
  if (counts.length === 1) return counts[0];
  const labels = (meta.score_overview_labels || "").split("|").map(s => s.trim());
  return counts.map((n, i) => labels[i] ? `${labels[i]}: ${n}` : n).join(" · ");
}

function renderScoreOverview(meta) {
  if (!meta.score_overview) return "";
  // più partiture: "url1 | url2" con etichette facoltative "Label 1 | Label 2"
  const srcs = meta.score_overview.split("|").map(s => s.trim()).filter(Boolean);
  const labels = (meta.score_overview_labels || "").split("|").map(s => s.trim());
  return srcs.map((src, i) => {
    const label = labels[i] || "";
    const alt = `${meta.title || "Score"}${label ? ` (${label})` : ""} — overview of all score pages`;
    return `
    <figure class="score-overview">
      ${label ? `<figcaption>${label}</figcaption>` : ""}
      <a href="${src}" target="_blank" rel="noopener">
        <img src="${src}" alt="${alt}" loading="lazy" decoding="async">
      </a>
    </figure>`;
  }).join("");
}

// -----------------------------
// Tabs behaviour
// -----------------------------
function initTabs() {
  const container = document.querySelector(".work-detail");
  if (!container) return;

  const buttons = container.querySelectorAll(".tabs button");
  const contents = container.querySelectorAll(".tab-content");
  const select = document.getElementById("tabs-dropdown");

  buttons.forEach(button => {
    button.addEventListener("click", () => {
      const tabId = button.dataset.tab;
      const target = container.querySelector(`#tab-${tabId}`);
      if (!target) return;

      buttons.forEach(b => b.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));

      button.classList.add("active");
      target.classList.add("active");

      if (select) select.value = tabId;
    });
  });

  if (select) {
    select.addEventListener("change", e => {
      const btn = container.querySelector(`.tabs button[data-tab="${e.target.value}"]`);
      btn?.click();
    });
  }
}

// -----------------------------
// Scroll to top content
// -----------------------------
function scrollWorkDetailToTop() {
  const detail = document.querySelector(".work-detail");
  if (!detail) return;

  const y = detail.getBoundingClientRect().top + window.pageYOffset - 20;
  window.scrollTo({ top: y, behavior: "smooth" });
}

// -----------------------------
// Set page title
// -----------------------------
function setPageTitle(title) {
  if (title) document.title = title + " | Works";
}
