document.addEventListener("DOMContentLoaded", () => {
  const html = document.documentElement;
  const toggleBtn = document.getElementById("toggle-dark");
  const iconPath = document.getElementById("icon-path");

  if (!toggleBtn || !iconPath) return;

  const moonPath = "M17.293 13.293a8 8 0 01-10.586-10.586 8 8 0 1010.586 10.586z";
  const sunPath = "M10 2a1 1 0 011 1v1a1 1 0 01-2 0V3a1 1 0 011-1zm4.22 2.22a1 1 0 011.414 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707zM18 10a1 1 0 110 2h-1a1 1 0 110-2h1zm-2.22 4.22a1 1 0 011.414 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707zM10 18a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zm-4.22-2.22a1 1 0 011.414 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707zM2 10a1 1 0 110 2H1a1 1 0 110-2h1zm2.22-4.22a1 1 0 011.414 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707z";

  function applyTheme(theme) {
    html.classList.toggle("dark", theme === "dark");
    iconPath.setAttribute("d", theme === "dark" ? moonPath : sunPath);
  }

  // Apply saved theme
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme) {
    applyTheme(savedTheme);
  } else {
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(systemPrefersDark ? "dark" : "light");
  }

  // Listen for system changes (if user hasn't chosen)
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
    if (!localStorage.getItem("theme")) {
      applyTheme(e.matches ? "dark" : "light");
    }
  });

  // Toggle click
  toggleBtn.addEventListener("click", () => {
    const newTheme = html.classList.contains("dark") ? "light" : "dark";
    applyTheme(newTheme);
    localStorage.setItem("theme", newTheme);
  });
});