(() => {
  const NEWS_LOCAL = "data/biotech-news.json";
  const NOTES_LOCAL = "data/biotech-notes.json";
  const NEWS_REMOTES = [
    "https://raw.githubusercontent.com/tylercheng00/tylercheng00/main/nanotech/data/biotech-news.json",
    "https://cdn.jsdelivr.net/gh/tylercheng00/tylercheng00@main/nanotech/data/biotech-news.json",
  ];
  const NOTES_REMOTES = [
    "https://raw.githubusercontent.com/tylercheng00/tylercheng00/main/nanotech/data/biotech-notes.json",
    "https://cdn.jsdelivr.net/gh/tylercheng00/tylercheng00@main/nanotech/data/biotech-notes.json",
  ];
  const NEWS_CACHE = "nanotech-biotech-news-v3";
  const NOTES_CACHE = "nanotech-biotech-notes-v2";
  const LANGS = ["zh-Hant", "zh-Hans", "en"];

  const newsList = document.getElementById("news-feed");
  const newsMeta = document.getElementById("news-updated");
  const notesList = document.getElementById("commentary-feed");
  const notesMeta = document.getElementById("notes-updated");

  let newsFeed = null;
  let notesFeed = null;

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

  /** Allow only http(s) or relative paths — blocks javascript:/data:/etc. */
  function safeHref(raw) {
    const value = String(raw || "").trim();
    if (!value || value === "#") return "#";
    // Protocol-relative //evil.example is treated as http(s) via URL parse below.
    if (/^https?:\/\//i.test(value)) {
      try {
        const u = new URL(value);
        if (u.protocol === "http:" || u.protocol === "https:") {
          return escapeHtml(u.href);
        }
      } catch {
        return "#";
      }
      return "#";
    }
    // Relative path only (no scheme). Reject "javascript:..." and "data:...".
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(value)) return "#";
    if (value.startsWith("//")) return "#";
    if (value.startsWith("/") || value.startsWith("./") || value.startsWith("../") || !value.includes(":")) {
      return escapeHtml(value);
    }
    return "#";
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
        timeZone: "Asia/Hong_Kong",
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
      if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10);
      const locale = lang === "en" ? "en-GB" : lang === "zh-Hans" ? "zh-CN" : "zh-HK";
      return new Intl.DateTimeFormat(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "Asia/Hong_Kong",
      }).format(d);
    } catch {
      return String(iso).slice(0, 10);
    }
  }

  function readCache(key) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function writeCache(key, feed) {
    try {
      localStorage.setItem(key, JSON.stringify(feed));
    } catch {
      /* ignore quota */
    }
  }

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function itemTime(item) {
    const raw = item && (item.publishedAt || item.day);
    const t = Date.parse(raw || 0);
    return Number.isNaN(t) ? 0 : t;
  }

  function newsScore(feed) {
    const items = Array.isArray(feed && feed.items) ? feed.items : [];
    const now = Date.now();
    let recent = 0;
    let newest = 0;
    for (const item of items) {
      const t = itemTime(item);
      if (t > newest) newest = t;
      if (t && now - t < 5 * 86400000) recent += 1;
    }
    return {
      recent,
      newest,
      updated: Date.parse((feed && feed.updatedAt) || 0) || 0,
    };
  }

  function betterNews(a, b) {
    if (!a) return b;
    if (!b) return a;
    const fa = newsScore(a);
    const fb = newsScore(b);
    if (fa.recent !== fb.recent) return fa.recent > fb.recent ? a : b;
    if (fa.newest !== fb.newest) return fa.newest > fb.newest ? a : b;
    return fa.updated >= fb.updated ? a : b;
  }

  function betterNotes(a, b) {
    if (!a) return b;
    if (!b) return a;
    const na = Array.isArray(a.articles) ? a.articles.length : 0;
    const nb = Array.isArray(b.articles) ? b.articles.length : 0;
    const da = String(a.day || "");
    const db = String(b.day || "");
    // Prefer a fuller history list, then the newer Hong Kong day, then fresher update.
    if (na !== nb && (na >= 5 || nb >= 5)) {
      if (Math.abs(na - nb) >= 3) return na > nb ? a : b;
    }
    if (da !== db) return da > db ? a : b;
    if (na !== nb) return na > nb ? a : b;
    const ta = Date.parse(a.updatedAt || 0) || 0;
    const tb = Date.parse(b.updatedAt || 0) || 0;
    return ta >= tb ? a : b;
  }

  function renderNews(feed) {
    if (!newsList || !feed) return;
    const lang = currentLang();
    const items = Array.isArray(feed.items) ? feed.items : [];
    if (newsMeta) {
      const stamp = formatStamp(feed.updatedAt, lang);
      newsMeta.innerHTML = `
        <span class="zh-hant">新聞資料更新：${escapeHtml(stamp)}（香港時間，約每 6 小時。只保留約 12 日內的消息。）</span>
        <span class="zh-hans">新闻资料更新：${escapeHtml(stamp)}（香港时间，约每 6 小时。只保留约 12 日内的消息。）</span>
        <span class="en">News feed updated: ${escapeHtml(stamp)} (Hong Kong time, about every 6 hours. Items older than about 12 days are dropped.)</span>
      `;
      newsMeta.hidden = !feed.updatedAt;
    }
    if (!items.length) {
      newsList.innerHTML = `
        <li class="insight-item">
          <p class="zh-hant">暫時未能載入新聞。請稍後再試。</p>
          <p class="zh-hans">暂时未能载入新闻。请稍后再试。</p>
          <p class="en">News could not be loaded. Please try again later.</p>
        </li>`;
      return;
    }
    newsList.innerHTML = items
      .map((item) => {
        const title = escapeHtml(pick(item.title, lang));
        const summary = escapeHtml(pick(item.summary, lang));
        const linkLabel = escapeHtml(pick(item.linkLabel, lang) || item.source || "Source");
        const note = escapeHtml(pick(item.langNote, lang));
        const when = formatPub(item.publishedAt, lang);
        const meta = escapeHtml([when, item.source].filter(Boolean).join(" · "));
        const url = safeHref(item.url);
        const same = title && summary && title === summary;
        return `
          <li class="insight-item is-visible">
            <div class="insight-meta">${meta}</div>
            <h3>${title}</h3>
            ${same ? "" : `<p>${summary}</p>`}
            ${note ? `<p class="insight-lang-note">${note}</p>` : ""}
            <a class="ext-link" href="${url}" target="_blank" rel="noopener noreferrer">${linkLabel}</a>
          </li>`;
      })
      .join("");
  }

  function renderNotes(feed) {
    if (!notesList || !feed) return;
    const lang = currentLang();
    const articles = Array.isArray(feed.articles) ? feed.articles : [];
    if (notesMeta) {
      const day = feed.day || "";
      const n = articles.length;
      const hist = feed.historyDays || 1;
      notesMeta.innerHTML = `
        <span class="zh-hant">${escapeHtml(day)}（香港日期）· 每日五則；顯示近 ${escapeHtml(String(hist))} 日共 ${escapeHtml(String(n))} 則</span>
        <span class="zh-hans">${escapeHtml(day)}（香港日期）· 每日五则；显示近 ${escapeHtml(String(hist))} 日共 ${escapeHtml(String(n))} 则</span>
        <span class="en">${escapeHtml(day)} (Hong Kong date) · five notes/day; showing ${escapeHtml(String(n))} across the last ${escapeHtml(String(hist))} days</span>
      `;
      notesMeta.hidden = !day;
    }
    if (!articles.length) {
      notesList.innerHTML = `
        <article class="insight-item">
          <p class="zh-hant">今日的五則短評尚未寫好。</p>
          <p class="zh-hans">今日的五则短评尚未写好。</p>
          <p class="en">Today's five notes are not ready yet.</p>
        </article>`;
      return;
    }
    notesList.innerHTML = articles
      .map((item) => {
        const when = formatPub(item.publishedAt, lang);
        const meta = escapeHtml([when, item.source].filter(Boolean).join(" · "));
        const url = safeHref(item.url);
        return `
          <article class="insight-item insight-commentary is-visible">
            <div class="insight-meta">${meta}</div>
            <h3 class="zh-hant">${escapeHtml(pick(item.title, "zh-Hant"))}</h3>
            <h3 class="zh-hans">${escapeHtml(pick(item.title, "zh-Hans"))}</h3>
            <h3 class="en">${escapeHtml(pick(item.title, "en"))}</h3>
            <p class="zh-hant">${escapeHtml(pick(item.body, "zh-Hant"))}</p>
            <p class="zh-hans">${escapeHtml(pick(item.body, "zh-Hans"))}</p>
            <p class="en">${escapeHtml(pick(item.body, "en"))}</p>
            <a class="ext-link" href="${url}" target="_blank" rel="noopener noreferrer"><span class="zh-hant">看原文</span><span class="zh-hans">看原文</span><span class="en">Source</span></a>
          </article>`;
      })
      .join("");
  }

  async function gather(localUrl, remotes) {
    const jobs = [fetchJson(localUrl)].concat(
      remotes.map((url) => fetchJson(`${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`))
    );
    const results = await Promise.allSettled(jobs);
    const ok = [];
    results.forEach((result, index) => {
      if (result.status === "fulfilled" && result.value) {
        result.value._from = index === 0 ? "local" : "remote";
        ok.push(result.value);
      }
    });
    return ok;
  }

  async function loadNews() {
    if (!newsList) return;
    const cached = readCache(NEWS_CACHE);
    if (cached && cached.items) renderNews(cached);
    const found = await gather(NEWS_LOCAL, NEWS_REMOTES);
    let best = cached && cached.items ? cached : null;
    for (const feed of found) {
      if (!feed.items) continue;
      best = betterNews(best, feed);
    }
    if (!best) {
      newsList.innerHTML = `
        <li class="insight-item">
          <p class="zh-hant">無法取得新聞資料。</p>
          <p class="zh-hans">无法取得新闻资料。</p>
          <p class="en">Unable to load the news feed.</p>
        </li>`;
      return;
    }
    newsFeed = best;
    writeCache(NEWS_CACHE, best);
    renderNews(best);
  }

  async function loadNotes() {
    if (!notesList) return;
    const cached = readCache(NOTES_CACHE);
    if (cached && cached.articles) renderNotes(cached);
    const found = await gather(NOTES_LOCAL, NOTES_REMOTES);
    let best = cached && cached.articles ? cached : null;
    for (const feed of found) {
      if (!feed.articles) continue;
      best = betterNotes(best, feed);
    }
    if (!best) return;
    notesFeed = best;
    writeCache(NOTES_CACHE, best);
    renderNotes(best);
  }

  document.querySelectorAll(".lang-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (newsFeed) renderNews(newsFeed);
      if (notesFeed) renderNotes(notesFeed);
    });
  });

  loadNews();
  loadNotes();
})();
