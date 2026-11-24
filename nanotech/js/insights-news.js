(() => {
  const FEED_LOCAL = "data/biotech-news.json";
  const FEED_REMOTE =
    "https://raw.githubusercontent.com/tylercheng00/tylercheng00/main/nanotech/data/biotech-news.json";
  const CACHE_KEY = "nanotech-biotech-news-v1";
  const listEl = document.getElementById("news-feed");
  const metaEl = document.getElementById("news-updated");
  if (!listEl) return;

  const LANGS = ["zh-Hant", "zh-Hans", "en"];

  function currentLang() {
    const lang = document.documentElement.lang;
    return LANGS.includes(lang) ? lang : "zh-Hant";
  }

  function pick(map, lang) {
    if (!map || typeof map !== "object") return "";
    return map[lang] || map.en || map["zh-Hant"] || map["zh-Hans"] || "";
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatStamp(iso, lang) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
      const locale = lang === "en" ? "en-GB" : lang === "zh-Hans" ? "zh-CN" : "zh-HK";
      return new Intl.DateTimeFormat(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
        timeZoneName: "short",
      }).format(d);
    } catch {
      return iso.slice(0, 10);
    }
  }

  function formatPub(iso, lang) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
      const locale = lang === "en" ? "en-GB" : lang === "zh-Hans" ? "zh-CN" : "zh-HK";
      return new Intl.DateTimeFormat(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(d);
    } catch {
      return iso.slice(0, 10);
    }
  }

  function readCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function writeCache(feed) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(feed));
    } catch {
      /* ignore */
    }
  }

  async function fetchFeed(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function newer(a, b) {
    const ta = Date.parse(a?.updatedAt || 0) || 0;
    const tb = Date.parse(b?.updatedAt || 0) || 0;
    return ta >= tb ? a : b;
  }

  function render(feed) {
    const lang = currentLang();
    const items = Array.isArray(feed.items) ? feed.items : [];
    if (metaEl) {
      const stamp = formatStamp(feed.updatedAt, lang);
      metaEl.innerHTML = `
        <span class="zh-hant">新聞資料更新：${escapeHtml(stamp)}（約每 6 小時）</span>
        <span class="zh-hans">新闻资料更新：${escapeHtml(stamp)}（约每 6 小时）</span>
        <span class="en">News feed updated: ${escapeHtml(stamp)} (about every 6 hours)</span>
      `;
      metaEl.hidden = !feed.updatedAt;
    }

    if (!items.length) {
      listEl.innerHTML = `
        <li class="insight-item">
          <p class="zh-hant">暫時未能載入新聞。請稍後再試。</p>
          <p class="zh-hans">暂时未能载入新闻。请稍后再试。</p>
          <p class="en">News could not be loaded. Please try again later.</p>
        </li>`;
      return;
    }

    listEl.innerHTML = items
      .map((item) => {
        const title = escapeHtml(pick(item.title, lang));
        const summary = escapeHtml(pick(item.summary, lang));
        const linkLabel = escapeHtml(pick(item.linkLabel, lang) || item.source || "Source");
        const note = escapeHtml(pick(item.langNote, lang));
        const when = formatPub(item.publishedAt, lang);
        const meta = escapeHtml([when, item.source].filter(Boolean).join(" · "));
        const url = escapeHtml(item.url || "#");
        return `
          <li class="insight-item is-visible">
            <div class="insight-meta">${meta}</div>
            <h3>${title}</h3>
            <p>${summary}</p>
            ${note ? `<p class="insight-lang-note">${note}</p>` : ""}
            <a class="ext-link" href="${url}" target="_blank" rel="noopener noreferrer">${linkLabel}</a>
          </li>`;
      })
      .join("");
  }

  async function load() {
    const cached = readCache();
    if (cached?.items?.length) render(cached);

    const results = await Promise.allSettled([
      fetchFeed(FEED_LOCAL),
      fetchFeed(`${FEED_REMOTE}?t=${Date.now()}`),
    ]);

    let best = cached;
    for (const r of results) {
      if (r.status === "fulfilled" && r.value?.items) {
        best = best ? newer(best, r.value) : r.value;
      }
    }

    if (!best) {
      listEl.innerHTML = `
        <li class="insight-item">
          <p class="zh-hant">無法取得新聞資料。</p>
          <p class="zh-hans">无法取得新闻资料。</p>
          <p class="en">Unable to load the news feed.</p>
        </li>`;
      return;
    }

    writeCache(best);
    render(best);
  }

  // Re-render on language switch
  document.querySelectorAll(".lang-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const cached = readCache();
      if (cached) render(cached);
    });
  });

  load();
})();
