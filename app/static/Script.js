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

const btn = document.getElementById("btn");

if (btn) {
  window.onscroll = () => {
      btn.style.display = window.scrollY > 300 ? "block" : "none";
  };
  
  btn.onclick = () => window.scrollTo({ top:0, behavior: "smooth"});
}

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

// Like Post
const likedPosts = new Set();

// Event delegation: handle all like buttons dynamically
document.addEventListener("click", function(e) {
  const btn = e.target.closest(".like-btn");
  if (!btn) return; // Ignore clicks outside buttons

  const postId = btn.dataset.postId;
  if (likedPosts.has(postId)) return; // Prevent multiple clicks

  const countSpan = btn.querySelector(".like-count");

  // Optimistic UI: increment count immediately
  countSpan.textContent = parseInt(countSpan.textContent) + 1;
  likedPosts.add(postId);

  // Animate button
  btn.classList.add("animate-bounce");
  setTimeout(() => btn.classList.remove("animate-bounce"), 500);

  // Send POST to server
  fetch(`/public/post/${postId}/like`, { method: "POST" })
    .then(res => res.json())
    .then(data => {
      // Sync server count
      countSpan.textContent = data.count;

      if (!data.liked) {
        // Already liked on server, revert Set
        likedPosts.delete(postId);
      }
    })
    .catch(err => {
      console.error("Like error:", err);
      // Revert optimistic UI
      countSpan.textContent = parseInt(countSpan.textContent) - 1;
      likedPosts.delete(postId);
    });
});

// Share
window.sharePost = function(postId, title) {
  const url = window.location.href;

  fetch(`/post/${postId}/share`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": csrf_token
    }
  })
  .then(res => res.json())
  .then(data => console.log("Share recorded:", data))
  .catch(err => console.error("Share error:", err));

  if (navigator.share) {
    navigator.share({ title, url });
  } else {
    navigator.clipboard.writeText(url);
    alert("Link copied to clipboard!");
  }
}

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