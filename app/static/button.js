  document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll("[data-safe]").forEach(btn => {
      let loading = false;

      btn.addEventListener("click", (e) => {
        if (loading) {
          e.preventDefault();
          return;
        }

        loading = true;

        const originalHTML = btn.innerHTML;
        btn.dataset.original = originalHTML;

        // Loading UI
        btn.classList.add("pointer-events-none", "opacity-70");
        btn.innerHTML = `
          <span class="w-4 h-4 border-2 border-white/60 border-t-white rounded-full animate-spin"></span>
          <span>Loading…</span>
        `;

        // Fallback recovery (prevents dead buttons)
        setTimeout(() => {
          recover(btn);
        }, 8000);
      });
    });

    function recover(btn) {
      btn.classList.remove("pointer-events-none", "opacity-70");
      btn.innerHTML = btn.dataset.original || "Retry";
    }

  });
  
  function showGlobalError(msg = "Something went wrong. Please try again.") {
    const err = document.getElementById("globalError");
    err.textContent = msg;
    err.classList.remove("hidden");
  }