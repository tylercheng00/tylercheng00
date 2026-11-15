(() => {
  const root = document.documentElement;
  const STORAGE_KEY = "nanotech-lang";

  function setLang(lang) {
    const next = lang === "en" ? "en" : "zh-Hant";
    root.lang = next;
    localStorage.setItem(STORAGE_KEY, next);
    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.lang === next));
    });
  }

  const saved = localStorage.getItem(STORAGE_KEY);
  setLang(saved || "zh-Hant");

  document.querySelectorAll(".lang-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => setLang(btn.dataset.lang));
  });

  const header = document.querySelector(".site-header");
  if (header) {
    const onScroll = () => {
      header.classList.toggle("is-scrolled", window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    links.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => {
        links.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  const revealEls = document.querySelectorAll(".reveal");
  if (revealEls.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  }

  const form = document.querySelector("#contact-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = new FormData(form);
      const name = String(data.get("name") || "").trim();
      const org = String(data.get("org") || "").trim();
      const email = String(data.get("email") || "").trim();
      const topic = String(data.get("topic") || "").trim();
      const message = String(data.get("message") || "").trim();
      const subject = encodeURIComponent(`[Nanotech] ${topic || "Enquiry"} — ${name}`);
      const body = encodeURIComponent(
        `Name / 姓名: ${name}\nOrganisation / 機構: ${org}\nEmail / 電郵: ${email}\nTopic / 主題: ${topic}\n\n${message}`
      );
      window.location.href = `mailto:info@tylerfuture.com?subject=${subject}&body=${body}`;
    });
  }
})();
