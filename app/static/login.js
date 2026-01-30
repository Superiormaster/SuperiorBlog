  const btn = document.getElementById("googleBtn");
  const text = document.getElementById("googleText");
  const icon = document.getElementById("googleIcon");
  const spinner = document.getElementById("googleSpinner");
  const error = document.getElementById("googleError");

  let isLoading = false;

  btn.addEventListener("click", (e) => {
    if (isLoading) {
      e.preventDefault();
      return;
    }

    try {
      isLoading = true;

      // UI: loading state
      text.textContent = "Signing you in…";
      icon.classList.add("hidden");
      spinner.classList.remove("hidden");
      btn.classList.add("pointer-events-none", "opacity-70");

      // Safety fallback (in case redirect fails)
      setTimeout(() => {
        showError();
      }, 8000);

    } catch (err) {
      e.preventDefault();
      showError();
    }
  });

  function showError() {
    isLoading = false;

    text.textContent = "Sign in with Google";
    icon.classList.remove("hidden");
    spinner.classList.add("hidden");
    btn.classList.remove("pointer-events-none", "opacity-70");
    error.classList.remove("hidden");
  }