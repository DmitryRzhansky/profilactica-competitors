(() => {
  const sidebar = document.getElementById("sidebar");
  const menuToggle = document.getElementById("menu-toggle");
  const backdrop = document.getElementById("drawer-backdrop");

  const setMenuOpen = (open) => {
    if (!sidebar || !menuToggle || !backdrop) return;
    sidebar.classList.toggle("is-open", open);
    menuToggle.setAttribute("aria-expanded", String(open));
    backdrop.hidden = !open;
    document.body.style.overflow = open ? "hidden" : "";
  };

  menuToggle?.addEventListener("click", () => {
    setMenuOpen(!sidebar.classList.contains("is-open"));
  });
  backdrop?.addEventListener("click", () => setMenuOpen(false));
  sidebar?.querySelectorAll("a[href^='#']").forEach((link) => {
    link.addEventListener("click", () => setMenuOpen(false));
  });

  const navLinks = [...document.querySelectorAll('.sidebar__nav a[href^="#"]')];
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  const syncActive = () => {
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= 120) current = section;
    }
    navLinks.forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("href") === `#${current.id}`);
    });
  };

  window.addEventListener("scroll", syncActive, { passive: true });
  syncActive();
})();
