document.addEventListener("DOMContentLoaded", () => {
    const ad = document.getElementById("page-transition-ad");
    const closeBtn = document.getElementById("close-transition-ad");
    const modal = document.getElementById("page-transition-ad");

    if (modal) {
        document.body.appendChild(modal);
    }

    if (!ad || !closeBtn) return;

    let pendingUrl = null;

    document.querySelectorAll("a[data-redirect]").forEach(link => {
        link.addEventListener("click", function (e) {
            e.preventDefault();

            pendingUrl = this.href;
            ad.classList.remove("hidden");
            document.body.style.overflow = "hidden";
        });
    });

    closeBtn.addEventListener("click", () => {
        ad.classList.add("hidden");
        document.body.style.overflow = "";

        if (pendingUrl) {
            window.location.href = pendingUrl;
        }
    });
});