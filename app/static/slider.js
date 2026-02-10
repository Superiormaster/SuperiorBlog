const openDrawer = document.getElementById('openDrawer');
const drawer = document.getElementById('mainDrawer');
const overlay = document.getElementById('drawerOverlay');

function openMenu() {
  drawer.classList.remove('translate-x-full');
  document.body.classList.add("drawer-open");
  overlay.classList.remove('hidden');
  document.documentElement.classList.add('overflow-hidden');
}

function closeMenu() {
  drawer.classList.add('translate-x-full');
  document.body.classList.remove("drawer-open");
  overlay.classList.add('hidden');
  document.documentElement.classList.remove('overflow-hidden');
}

openDrawer.addEventListener('click', openMenu);
overlay.addEventListener('click', closeMenu);

document.addEventListener("DOMContentLoaded", () => {
        const openDrawer = document.getElementById("openDrawer");
        const drawer = document.getElementById("mainDrawer");
        const overlay = document.getElementById("drawerOverlay");

        if (!openDrawer || !drawer || !overlay) return;

        function toggleDrawer(show) {
            const isVisible = show ?? drawer.getAttribute("aria-hidden") === "true";
            drawer.setAttribute("aria-hidden", !isVisible);
            overlay.dataset.hidden = !isVisible;
            openDrawer.setAttribute("aria-expanded", isVisible);
            document.body.style.overflow = isVisible ? "hidden" : "";
        }

        openDrawer.addEventListener("click", () => toggleDrawer(true));
        overlay.addEventListener("click", () => toggleDrawer(false));
});
