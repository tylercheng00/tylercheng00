(() => {
  const root = document.documentElement;
  const STORAGE_KEY = "nanotech-lang";
  const LANGS = ["zh-Hant", "zh-Hans", "en"];

  root.classList.add("js");

  function readStoredLang() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }

  function writeStoredLang(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
  }

  function setLang(lang) {
    const next = LANGS.includes(lang) ? lang : "zh-Hant";
    root.lang = next;
    writeStoredLang(next);
    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.lang === next));
    });
  }

  setLang(readStoredLang() || root.lang || "zh-Hant");

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

  document.querySelectorAll(".flow-track").forEach((track) => {
    const steps = track.querySelectorAll(".flow-step");
    if (!("IntersectionObserver" in window)) {
      steps.forEach((s) => s.classList.add("is-on"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          steps.forEach((step, i) => {
            setTimeout(() => step.classList.add("is-on"), i * 160);
          });
          io.unobserve(entry.target);
        });
      },
      { threshold: 0.25 }
    );
    io.observe(track);
  });

  const canvas = document.getElementById("targeting-canvas");
  if (canvas && canvas.getContext) {
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let particles = [];
    let targeted = true;
    const toggleBtn = document.getElementById("targeting-toggle");

    function resize() {
      const rect = canvas.getBoundingClientRect();
      w = Math.max(320, Math.floor(rect.width));
      h = Math.max(240, Math.floor(rect.height));
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      initParticles();
    }

    function initParticles() {
      particles = Array.from({ length: 42 }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 1.2,
        vy: (Math.random() - 0.5) * 1.2,
        r: 2 + Math.random() * 2,
      }));
    }

    const tumours = [
      { x: 0.72, y: 0.38, r: 28 },
      { x: 0.62, y: 0.68, r: 20 },
    ];
    const healthy = [
      { x: 0.28, y: 0.32, r: 18 },
      { x: 0.38, y: 0.72, r: 22 },
      { x: 0.2, y: 0.58, r: 16 },
    ];

    function drawCell(c, color) {
      const x = c.x * w;
      const y = c.y * h;
      ctx.beginPath();
      ctx.arc(x, y, c.r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.35;
      ctx.fill();
      ctx.globalAlpha = 0.9;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    function step() {
      ctx.clearRect(0, 0, w, h);
      const g = ctx.createRadialGradient(w * 0.65, h * 0.45, 20, w * 0.5, h * 0.5, w * 0.7);
      g.addColorStop(0, "rgba(107,69,160,0.18)");
      g.addColorStop(1, "rgba(12,6,20,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      healthy.forEach((c) => drawCell(c, "#6b8cae"));
      tumours.forEach((c) => drawCell(c, "#c45c8a"));

      particles.forEach((p) => {
        if (targeted) {
          let best = null;
          let bestD = Infinity;
          tumours.forEach((c) => {
            const dx = c.x * w - p.x;
            const dy = c.y * h - p.y;
            const d = Math.hypot(dx, dy);
            if (d < bestD) {
              bestD = d;
              best = { dx, dy, d };
            }
          });
          if (best && best.d > 8) {
            p.vx += (best.dx / best.d) * 0.08;
            p.vy += (best.dy / best.d) * 0.08;
          }
        } else {
          p.vx += (Math.random() - 0.5) * 0.05;
          p.vy += (Math.random() - 0.5) * 0.05;
        }

        const speed = Math.hypot(p.vx, p.vy);
        if (speed > 2.2) {
          p.vx *= 2.2 / speed;
          p.vy *= 2.2 / speed;
        }

        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
        p.x = Math.max(0, Math.min(w, p.x));
        p.y = Math.max(0, Math.min(h, p.y));

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = targeted ? "#e8d7ff" : "#9aa3b5";
        ctx.fill();
      });

      requestAnimationFrame(step);
    }

    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        targeted = !targeted;
        toggleBtn.setAttribute("aria-pressed", String(targeted));
        toggleBtn.querySelectorAll("[data-mode]").forEach((el) => {
          el.hidden = el.dataset.mode !== (targeted ? "on" : "off");
        });
      });
    }

    resize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(step);
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
        `Name / 姓名: ${name}\nOrganisation / 机构/機構: ${org}\nEmail: ${email}\nTopic: ${topic}\n\n${message}`
      );
      window.location.href = `mailto:tyler.cheng@alumni.ust.hk?subject=${subject}&body=${body}`;
    });
  }
})();
