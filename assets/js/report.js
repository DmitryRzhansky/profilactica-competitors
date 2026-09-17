(() => {
  const PALETTE = ["#1a7fc4", "#0f5f9a", "#3d9ad1", "#6bb3dc", "#124e78", "#8ecae6", "#023047", "#4d8fb8"];
  const DEFAULT_RADAR = ["verimed.ru", "alcomed.ru", "ne-zavisimost.ru"];

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const formatInt = (n) => Number(n).toLocaleString("ru-RU");
  const formatNum = (n) => {
    const num = Number(n);
    return Number.isInteger(num) ? formatInt(num) : num.toLocaleString("ru-RU", { maximumFractionDigits: 1 });
  };

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

  const hasGeo = (policy) => {
    const v = (policy || "").trim();
    return v !== "" && v !== "Нет";
  };

  function parseCSV(text) {
    const rows = [];
    let row = [];
    let cur = "";
    let inQuotes = false;
    const pushRow = () => {
      row.push(cur);
      cur = "";
      if (row.some((x) => x !== "")) rows.push(row);
      row = [];
    };
    for (let i = 0; i < text.length; i += 1) {
      const c = text[i];
      const n = text[i + 1];
      if (inQuotes) {
        if (c === '"' && n === '"') {
          cur += '"';
          i += 1;
        } else if (c === '"') {
          inQuotes = false;
        } else {
          cur += c;
        }
      } else if (c === '"') {
        inQuotes = true;
      } else if (c === ",") {
        row.push(cur);
        cur = "";
      } else if (c === "\n") {
        pushRow();
      } else if (c === "\r") {
        if (n === "\n") i += 1;
        pushRow();
      } else {
        cur += c;
      }
    }
    if (cur !== "" || row.length) pushRow();
    const headers = rows.shift().map((h) => h.replace(/^\uFEFF/, ""));
    return rows.map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])));
  }

  async function loadText(url) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${url}: ${res.status}`);
      return res.text();
    } catch (err) {
      const embed = window.__REPORT_EMBED__;
      const map = {
        "./assets/data/report-data.json": embed && JSON.stringify(embed.json),
        "./assets/data/architecture.csv": embed && embed.architecture,
        "./assets/data/geo-master.csv": embed && embed.geoMaster,
        "./assets/data/geo-pages.csv": embed && embed.geoPages,
      };
      if (map[url]) return map[url];
      throw err;
    }
  }

  function getChartCtor() {
    if (typeof window.Chart === "function") return window.Chart;
    try {
      if (typeof module !== "undefined" && module.exports) {
        return module.exports.Chart || module.exports;
      }
    } catch (err) {}
    return null;
  }

  function waitForChart(timeout = 4000) {
    const found = getChartCtor();
    if (found) {
      window.Chart = found;
      return Promise.resolve(found);
    }
    return new Promise((resolve, reject) => {
      const started = Date.now();
      const timer = setInterval(() => {
        const ctor = getChartCtor();
        if (ctor) {
          window.Chart = ctor;
          clearInterval(timer);
          resolve(ctor);
        } else if (Date.now() - started > timeout) {
          clearInterval(timer);
          reject(new Error("Chart.js не загрузился"));
        }
      }, 30);
    });
  }

  function badgePriority(p) {
    const cls = p === "P0" ? "badge-p0" : p === "P1" ? "badge-p1" : "badge-p2";
    return `<span class="badge ${cls}">${p}</span>`;
  }

  function setupNav() {
    const sidebar = $("#sidebar");
    const menuToggle = $("#menu-toggle");
    const backdrop = $("#drawer-backdrop");
    const setOpen = (open) => {
      if (!sidebar || !menuToggle || !backdrop) return;
      sidebar.classList.toggle("is-open", open);
      menuToggle.setAttribute("aria-expanded", String(open));
      backdrop.hidden = !open;
      document.body.style.overflow = open ? "hidden" : "";
    };
    menuToggle?.addEventListener("click", () => setOpen(!sidebar.classList.contains("is-open")));
    backdrop?.addEventListener("click", () => setOpen(false));
    $$('.sidebar__nav a[href^="#"]').forEach((link) => {
      link.addEventListener("click", () => setOpen(false));
    });

    const navLinks = $$('.sidebar__nav a[href^="#"]');
    const sections = navLinks.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
    const sync = () => {
      let current = sections[0];
      for (const section of sections) {
        if (section.getBoundingClientRect().top <= 140) current = section;
      }
      navLinks.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${current.id}`);
      });
    };
    const observer = new IntersectionObserver(sync, { rootMargin: "-20% 0px -70% 0px", threshold: [0, 1] });
    sections.forEach((section) => observer.observe(section));
    window.addEventListener("scroll", sync, { passive: true });
    sync();
  }

  function renderKpis(data, architecture, geoPages, master) {
    const m = data.market;
    const otherUslugi = m.profilactica_uslugi - m.profilactica_geo;
    const rest = m.profilactica_pages - m.profilactica_uslugi;
    const kpis = [
      { value: formatInt(m.competitor_domains), label: "конкурентов" },
      { value: `~${formatInt(m.competitor_url_rows)}`, label: "URL конкурентов" },
      { value: formatInt(m.profilactica_pages), label: "URL текущего сайта" },
      { value: formatInt(m.profilactica_geo), label: "текущих ГЕО URL" },
      { value: formatInt(architecture.length), label: "страниц в финальной архитектуре" },
      { value: formatInt(data.planned_geo.core_geo_pages || geoPages.length), label: "URL в основной планируемой ГЕО-матрице" },
    ];
    $("#hero-kpi").innerHTML = kpis
      .map((k) => `<div class="kpi"><span class="kpi__value">${k.value}</span><span class="kpi__label">${k.label}</span></div>`)
      .join("");

    const geoKpi = [
      { value: formatInt(data.planned_geo.metro_entities), label: "метро/узлов" },
      { value: formatInt(data.planned_geo.okrug_entities), label: "округов" },
      { value: formatInt(data.planned_geo.mo_core_cities), label: "городов МО" },
      { value: formatInt(data.planned_geo.core_geo_pages || geoPages.length), label: "URL в рабочей матрице" },
    ];
    const geoBox = $("#geo-kpi");
    if (geoBox) {
      geoBox.innerHTML = geoKpi
        .map((k) => `<div class="kpi"><span class="kpi__value">${k.value}</span><span class="kpi__label">${k.label}</span></div>`)
        .join("");
    }
    return { otherUslugi, rest };
  }

  let chartsReady = false;
  let geoReady = false;

  function makeStaticCharts(data, composition) {
    const ChartCtor = getChartCtor();
    if (!ChartCtor || chartsReady) return;
    chartsReady = true;
    window.Chart = ChartCtor;
    ChartCtor.defaults.font.family = "Inter, Arial, sans-serif";
    ChartCtor.defaults.color = "#5a6570";
    ChartCtor.defaults.borderColor = "#e3e9ef";

    const m = data.market;
    const make = (canvas, config) => {
      try {
        if (canvas) new ChartCtor(canvas, config);
      } catch (err) {
        console.error(err);
      }
    };
    make($("#chart-market-size"), {
      type: "bar",
      data: {
        labels: ["profilactica.clinic", "Медиана рынка", "Среднее рынка"],
        datasets: [
          {
            label: "Страниц",
            data: [m.profilactica_pages, m.market_median_pages, m.market_average_pages],
            backgroundColor: [PALETTE[0], PALETTE[4], PALETTE[2]],
            borderRadius: 4,
            maxBarThickness: 64,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });

    make($("#chart-site-composition"), {
      type: "doughnut",
      data: {
        labels: ["ГЕО URL", "Прочие /uslugi/", "Остальные страницы"],
        datasets: [
          {
            data: [m.profilactica_geo, composition.otherUslugi, composition.rest],
            backgroundColor: [PALETTE[0], PALETTE[2], PALETTE[5]],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        cutout: "58%",
      },
    });

    const geoLabels = Object.keys(data.geo_adoption_domains);
    const geoValues = Object.values(data.geo_adoption_domains);
    make($("#chart-geo-adoption"), {
      type: "bar",
      data: {
        labels: geoLabels,
        datasets: [
          {
            label: "Доменов",
            data: geoValues,
            backgroundColor: PALETTE[0],
            borderRadius: 3,
            maxBarThickness: 22,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } },
      },
    });

    const oppEntries = Object.entries(data.opportunity_scores).sort((a, b) => b[1] - a[1]);
    make($("#chart-opportunities"), {
      type: "bar",
      data: {
        labels: oppEntries.map((x) => x[0]),
        datasets: [
          {
            label: "Приоритет",
            data: oppEntries.map((x) => x[1]),
            backgroundColor: PALETTE[1],
            borderRadius: 3,
            maxBarThickness: 18,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, max: 100 } },
      },
    });

    const radar = data.competitor_radar;
    const radarBox = $("#radar-controls");
    const radarState = {};
    if (radarBox) {
      Object.keys(radar.series).forEach((domain, i) => {
        radarState[domain] = DEFAULT_RADAR.includes(domain);
        const id = `radar-${i}`;
        radarBox.insertAdjacentHTML(
          "beforeend",
          `<label><input type="checkbox" id="${id}" ${radarState[domain] ? "checked" : ""}> ${domain}</label>`
        );
        $(`#${id}`).addEventListener("change", (e) => {
          radarState[domain] = e.target.checked;
          redrawRadar();
        });
      });
    }

    let radarChart;
    function redrawRadar() {
      const datasets = Object.entries(radar.series)
        .filter(([domain]) => radarState[domain])
        .map(([domain, values], i) => ({
          label: domain,
          data: values,
          borderColor: PALETTE[i % PALETTE.length],
          backgroundColor: `${PALETTE[i % PALETTE.length]}33`,
          pointBackgroundColor: PALETTE[i % PALETTE.length],
          borderWidth: 2,
        }));
      const cfg = {
        type: "radar",
        data: { labels: radar.axes, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom" } },
          scales: { r: { min: 0, max: 10, ticks: { stepSize: 2, showLabelBackdrop: false } } },
        },
      };
      if (radarChart) {
        radarChart.data = cfg.data;
        radarChart.update();
      } else {
        const canvas = $("#chart-competitor-radar");
        if (canvas) radarChart = new ChartCtor(canvas, cfg);
      }
    }
    redrawRadar();
  }

  function makeGeoChart(geoPages) {
    const ChartCtor = getChartCtor();
    if (!ChartCtor || geoReady || !geoPages.length) return;
    geoReady = true;
    window.Chart = ChartCtor;
    const matrix = {};
    geoPages.forEach((row) => {
      const name = row.service_name;
      matrix[name] ||= { metro: 0, okrug: 0, mo: 0 };
      if (matrix[name][row.geo_type] !== undefined) matrix[name][row.geo_type] += 1;
    });
    const serviceOrder = [...new Set(geoPages.map((r) => r.service_name))];
    const canvas = $("#chart-geo-plan");
    if (!canvas) return;
    new ChartCtor(canvas, {
      type: "bar",
      data: {
        labels: serviceOrder,
        datasets: [
          { label: "Метро", data: serviceOrder.map((s) => matrix[s].metro), backgroundColor: PALETTE[0], stack: "geo" },
          { label: "Округа", data: serviceOrder.map((s) => matrix[s].okrug), backgroundColor: PALETTE[2], stack: "geo" },
          { label: "МО", data: serviceOrder.map((s) => matrix[s].mo), backgroundColor: PALETTE[5], stack: "geo" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
      },
    });

    renderGeoMatrix(serviceOrder, matrix, geoPages);
  }

  function renderGeoMatrix(serviceOrder, matrix, geoPages) {
    const body = serviceOrder
      .map((name) => {
        const m = matrix[name];
        const total = m.metro + m.okrug + m.mo;
        return `<tr><td>${esc(name)}</td><td>${m.metro}</td><td>${m.okrug}</td><td>${m.mo}</td><td>${total}</td></tr>`;
      })
      .join("");
    const sum = geoPages.length;
    $("#geo-matrix-body").innerHTML =
      body +
      `<tr><th>Итого</th><th>${geoPages.filter((r) => r.geo_type === "metro").length}</th><th>${
        geoPages.filter((r) => r.geo_type === "okrug").length
      }</th><th>${geoPages.filter((r) => r.geo_type === "mo").length}</th><th>${sum}</th></tr>`;
  }

  function renderSilo(architecture) {
    const bySilo = new Map();
    architecture.forEach((row, idx) => {
      if (/^trust\s*\/\s*выбор$/i.test((row.silo || "").trim())) return;
      if (!bySilo.has(row.silo)) bySilo.set(row.silo, []);
      bySilo.get(row.silo).push({ ...row, idx });
    });

    const tree = $("#silo-tree");
    const html = [...bySilo.entries()]
      .map(([silo, rows]) => {
        const byParent = new Map();
        rows.forEach((row) => {
          const key = row.parent || "/";
          if (!byParent.has(key)) byParent.set(key, []);
          byParent.get(key).push(row);
        });
        const roots = rows.filter((r) => !rows.some((p) => p.url === r.parent));
        const renderNodes = (nodes, depth = 0) =>
          nodes
            .map((node) => {
              const children = rows.filter((r) => r.parent === node.url);
              const inner = children.length ? `<div class="tree-children">${renderNodes(children, depth + 1)}</div>` : "";
              const caret = children.length
                ? `<button class="icon-btn tree-caret" type="button" aria-expanded="true" aria-label="Свернуть ${node.page}"><i class="fa-solid fa-chevron-down" aria-hidden="true"></i></button>`
                : `<span class="tree-caret"></span>`;
              return `<div class="tree-node" data-url="${encodeURIComponent(node.url)}">
                <div class="tree-row ${children.length ? "is-parent" : ""}" data-row="${node.idx}">
                  ${caret}
                  <span class="tree-page">${esc(node.page)}</span>
                  ${badgePriority(node.priority)}
                  ${hasGeo(node.geo_policy) ? '<span class="badge badge-geo">ГЕО</span>' : ""}
                  <span class="mono">${esc(node.url)}</span>
                </div>
                ${inner}
              </div>`;
            })
            .join("");
        return `<div class="tree-group">
          <button class="tree-toggle" type="button" aria-expanded="true"><span class="tree-caret"><i class="fa-solid fa-folder-open" aria-hidden="true"></i></span>${esc(silo)} <span class="badge badge-p1">${rows.length}</span></button>
          <div class="tree-children">${renderNodes(roots)}</div>
        </div>`;
      })
      .join("");
    tree.innerHTML = html;

    tree.addEventListener("click", (e) => {
      const caret = e.target.closest(".tree-caret.icon-btn");
      if (caret) {
        const node = caret.closest(".tree-node");
        const kids = node.querySelector(":scope > .tree-children");
        const open = caret.getAttribute("aria-expanded") === "true";
        caret.setAttribute("aria-expanded", String(!open));
        caret.querySelector("i").className = open ? "fa-solid fa-chevron-right" : "fa-solid fa-chevron-down";
        if (kids) kids.hidden = open;
        return;
      }
      const groupBtn = e.target.closest(".tree-toggle");
      if (groupBtn) {
        const open = groupBtn.getAttribute("aria-expanded") === "true";
        groupBtn.setAttribute("aria-expanded", String(!open));
        const kids = groupBtn.nextElementSibling;
        if (kids) kids.hidden = open;
      }
    });
  }

  function setupReadMore() {
    $$(".read-more").forEach((wrap) => {
      const btn = wrap.querySelector(".read-more__btn");
      if (!btn) return;
      btn.addEventListener("click", () => {
        const keep = wrap.getBoundingClientRect().top;
        const open = wrap.classList.toggle("is-open");
        btn.setAttribute("aria-expanded", String(open));
        btn.textContent = open ? "Свернуть" : "Читать далее";
        const delta = wrap.getBoundingClientRect().top - keep;
        if (delta) window.scrollBy(0, delta);
      });
    });
  }

  function renderGeoLists(master) {
    const metro = master.filter((r) => r.geo_type === "metro");
    const okrug = master.filter((r) => r.geo_type === "okrug");
    const mo = master.filter((r) => r.geo_type === "mo");
    const chips = (rows) => rows.map((r) => `<span class="chip">${esc(r.name)}</span>`).join("");
    $("#geo-list-metro").innerHTML = chips(metro);
    $("#geo-list-okrug").innerHTML = chips(okrug);
    $("#geo-list-mo-t1").innerHTML = chips(mo.filter((r) => r.tier === "tier-1"));
    $("#geo-list-mo-t2").innerHTML = chips(mo.filter((r) => r.tier === "tier-2"));
    $("#metro-count").textContent = metro.length;
    $("#okrug-count").textContent = okrug.length;
    $("#mo-count").textContent = mo.length;
  }

  function pageWindow(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = new Set([1, total, current, current - 1, current + 1]);
    if (current <= 3) [2, 3, 4].forEach((n) => pages.add(n));
    if (current >= total - 2) [total - 3, total - 2, total - 1].forEach((n) => pages.add(n));
    return [...pages].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b);
  }

  function renderGeoCatalog(geoPages) {
    const services = [...new Set(geoPages.map((r) => r.service_name))];
    const types = [...new Set(geoPages.map((r) => r.geo_type))];
    $("#geo-filter-service").innerHTML =
      '<option value="">Все услуги</option>' + services.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("");
    $("#geo-filter-type").innerHTML =
      '<option value="">Все типы ГЕО</option>' + types.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("");

    const state = { service: "", type: "", q: "", page: 1, per: 50 };
    const tbody = $("#geo-catalog-body");
    const nav = $("#geo-pager-nav");

    const filtered = () => {
      const q = state.q.trim().toLowerCase();
      return geoPages.filter((r) => {
        if (state.service && r.service_name !== state.service) return false;
        if (state.type && r.geo_type !== state.type) return false;
        if (q) {
          const blob = `${r.service_name} ${r.geo_name} ${r.geo_slug} ${r.proposed_url}`.toLowerCase();
          if (!blob.includes(q)) return false;
        }
        return true;
      });
    };

    const paintPager = (pages) => {
      const nums = pageWindow(state.page, pages);
      let html = `<button class="pager__btn" type="button" data-page="${state.page - 1}" ${state.page <= 1 ? "disabled" : ""} aria-label="Предыдущая страница">‹</button>`;
      let prev = 0;
      nums.forEach((n) => {
        if (prev && n - prev > 1) html += `<span class="pager__ellipsis" aria-hidden="true">…</span>`;
        html += `<button class="pager__btn ${n === state.page ? "is-active" : ""}" type="button" data-page="${n}" ${n === state.page ? 'aria-current="page"' : ""}>${n}</button>`;
        prev = n;
      });
      html += `<button class="pager__btn" type="button" data-page="${state.page + 1}" ${state.page >= pages ? "disabled" : ""} aria-label="Следующая страница">›</button>`;
      nav.innerHTML = html;
    };

    const paint = () => {
      const rows = filtered();
      const pages = Math.max(1, Math.ceil(rows.length / state.per));
      if (state.page > pages) state.page = pages;
      const start = (state.page - 1) * state.per;
      const slice = rows.slice(start, start + state.per);
      tbody.innerHTML = slice
        .map(
          (r) => `<tr>
            <td>${esc(r.service_name)}</td>
            <td>${esc(r.geo_type)}</td>
            <td>${esc(r.geo_name)}</td>
            <td class="url-cell">${esc(r.proposed_url)}</td>
          </tr>`
        )
        .join("");
      paintPager(pages);
    };

    $("#geo-filter-service").addEventListener("change", (e) => {
      state.service = e.target.value;
      state.page = 1;
      paint();
    });
    $("#geo-filter-type").addEventListener("change", (e) => {
      state.type = e.target.value;
      state.page = 1;
      paint();
    });
    $("#geo-filter-search").addEventListener("input", (e) => {
      state.q = e.target.value;
      state.page = 1;
      paint();
    });
    $("#geo-per-page").addEventListener("change", (e) => {
      state.per = Number(e.target.value);
      state.page = 1;
      paint();
    });
    nav.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-page]");
      if (!btn || btn.disabled) return;
      const page = Number(btn.dataset.page);
      if (!page || page === state.page) return;
      state.page = page;
      paint();
      tbody.closest(".table-wrap")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    paint();
  }

  function setupScreenshots() {
    $$(".shot img").forEach((img) => {
      const shot = img.closest(".shot");
      const fail = () => shot?.classList.add("is-missing");
      img.addEventListener("error", fail);
      if (img.complete && !img.naturalWidth) fail();
    });
    $$("img.favicon[data-domain]").forEach((img) => {
      const fail = () => {
        const fallback = document.createElement("span");
        fallback.className = "favicon-fallback";
        fallback.textContent = (img.dataset.fallback || "?").slice(0, 2).toUpperCase();
        img.replaceWith(fallback);
      };
      if (img.getAttribute("src")) {
        img.addEventListener("error", fail);
        return;
      }
      const exts = ["png", "ico", "svg", "webp", "jpg"];
      let i = 0;
      const tryNext = () => {
        if (i >= exts.length) {
          fail();
          return;
        }
        img.src = `./assets/competitors/${img.dataset.domain}/favicon.${exts[i]}`;
        i += 1;
      };
      img.addEventListener("error", tryNext);
      tryNext();
    });
  }

  async function init() {
    setupNav();
    setupScreenshots();
    setupReadMore();
    await waitForChart();
    const [jsonText, archText, masterText] = await Promise.all([
      loadText("./assets/data/report-data.json"),
      loadText("./assets/data/architecture.csv"),
      loadText("./assets/data/geo-master.csv"),
    ]);
    const data = JSON.parse(jsonText);
    const architecture = parseCSV(archText);
    const master = parseCSV(masterText);

    let geoPages = null;
    const loadGeo = async () => {
      if (geoPages) return geoPages;
      geoPages = parseCSV(await loadText("./assets/data/geo-pages.csv"));
      return geoPages;
    };

    const composition = renderKpis(data, architecture, { length: data.planned_geo.core_geo_pages }, master);
    renderSilo(architecture);
    renderGeoLists(master);
    makeStaticCharts(data, composition);

    let geoBooted = false;
    const bootGeo = async () => {
      if (geoBooted) return;
      geoBooted = true;
      const pages = await loadGeo();
      renderKpis(data, architecture, pages, master);
      makeGeoChart(pages);
      renderGeoCatalog(pages);
    };

    const observe = (el) => {
      if (!el) return;
      if (!("IntersectionObserver" in window)) {
        bootGeo();
        return;
      }
      const obs = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            obs.disconnect();
            bootGeo();
          }
        },
        { rootMargin: "240px" }
      );
      obs.observe(el);
    };
    observe($("#geo"));
    observe($("#chart-geo-plan")?.closest(".chart-card"));

    window.addEventListener("beforeprint", () => {
      $$("details").forEach((d) => d.setAttribute("open", ""));
      $$(".tree-children").forEach((el) => {
        el.hidden = false;
      });
    });
  }

  let started = false;
  const start = () => {
    if (started) return;
    started = true;
    init().catch((err) => {
      console.error(err);
      const hero = $("#hero-kpi");
      if (hero) hero.innerHTML = `<p class="note">Не удалось загрузить данные отчета.</p>`;
    });
  };
  document.addEventListener("DOMContentLoaded", start);
  if (document.readyState !== "loading") start();
})();
