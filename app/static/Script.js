// scroll
window.addEventListener("scroll", () => {
  const header = document.querySelector("header.navbar");
  if (!header) return;

  if (window.scrollY > 50) {
    header.classList.add("shadow-lg");
  } else {
    header.classList.remove("shadow-lg");
  }
});

window.addEventListener('load', () => {
  document.body.classList.add('ready');
});

/* Page Load-more */
let page = 1;
let loading = false;
let hasMore = true;

window.addEventListener("scroll", () => {
  if (loading || !hasMore) return;

  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
    loading = true;
    page++;

    fetch(`/load-more?page=${page}`)
      .then(res => res.json())
      .then(data => {
        // ✅ STOP if no more posts
        if (!data.has_more) {
          hasMore = false;
        }

        // ✅ Append new posts
        if (data.html.trim() !== "") {
          document
            .getElementById("post-container")
            ?.insertAdjacentHTML("beforeend", data.html);
        }

        loading = false;
      })
      .catch(() => {
        loading = false;
      });
  }
});

// Latest Post Slider
const latestSlider = document.getElementById("latest-slider");

if (latestSlider) {
  let index = 0;
  const total = latestSlider.children.length;

  setInterval(() => {
    index = (index + 1) % total;
    latestSlider.style.transform = `translateX(-${index * 100}%)`;
  }, 5000);
}

// Trending Post Slider
const trendingSlider = document.getElementById('trending-slider');

if (trendingSlider) {
  let scrollAmount = 0;

  function autoScroll() {
    scrollAmount += 1;
    if (scrollAmount >= trendingSlider.scrollWidth - trendingSlider.clientWidth) {
      scrollAmount = 0;
    }
    trendingSlider.scrollTo({
      left: scrollAmount,
      behavior: 'smooth'
    });
    requestAnimationFrame(autoScroll);
  }

  autoScroll();
}

// GOOGLE HANDLER
function handleCredentialResponse(response) {
    // This will send the credential (JWT) to your Flask backend
    fetch("/auth/google/onetap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // Redirect after login
            window.location.href = "/dashboard";
        } else {
            alert("Login failed. Try again.");
        }
    });
}

// Initialize One Tap
window.onload = () => {
    google.accounts.id.initialize({
        client_id: "{{ GOOGLE_CLIENT_ID }}",  // replace with your actual CLIENT_ID
        callback: handleCredentialResponse,
        auto_select: true           // don’t auto-login; show chooser
        cancel_on_tap_outside: false
    });

    google.accounts.id.prompt();       // show the account chooser
};