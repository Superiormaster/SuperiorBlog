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