// PULL_OUT DASHBOARD

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

const btn = document.getElementById("btn");

window.onscroll = () => {
    btn.style.display = window.scrollY > 300 ? "block" : "none";
};

btn.onclick = () => window.scrollTo({ top:0, behavior: "smooth"});

window.addEventListener('load', () => {
  document.body.classList.add('ready');
});

/* Page Load-more */
let page = 1;
let loading = false;

window.addEventListener("scroll", () => {
  if (loading) return;

  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
    loading = true;
    page++;

    fetch(`/load-more?page=${page}`)
      .then(res => res.text())
      .then(html => {
        document
          .getElementById("post-container")
          ?.insertAdjacentHTML("beforeend", html);
        loading = false;
      });
  }
});

  // Wait for the page to load
  document.addEventListener("DOMContentLoaded", () => {
    const messages = document.querySelectorAll('.fixed.top-5.right-5 .px-4');

    messages.forEach((msg) => {
      // Set a timeout to fade out
      setTimeout(() => {
        // Smoothly fade out
        msg.style.transition = "opacity 0.5s ease, transform 0.5s ease";
        msg.style.opacity = "0";
        msg.style.transform = "translateY(-20px)";

        // Remove the element from DOM after transition
        setTimeout(() => msg.remove(), 500);
      }, 3000); // <-- 3 seconds before disappearing
    });
  });

// Like Post
const likedPosts = new Set();

function likePost(id) {
  if (likedPosts.has(id)) return;

  fetch(`/post/${id}/like`, { method: "POST" })
    .then(res => res.json())
    .then(data => {
      if (data.liked) {
        document.getElementById(`like-count-${id}`).textContent = data.count;
        likedPosts.add(id);
      }
    });
}

// Comment 
function toggleComments() {
  const section = document.getElementById("comment-section");
  section.classList.toggle("hidden");
  section.scrollIntoView({ behavior: "smooth" });
}

// Share
function sharePost(title) {
  const url = window.location.href;

  if (navigator.share) {
    navigator.share({ title, url });
  } else {
    navigator.clipboard.writeText(url);
    alert("Link copied to clipboard!");
  }
}

// Latest Post Slider
let index = 0;
const latestSlider = document.getElementById("latest-slider");
const total = latestSlider.children.length;

setInterval(() => {
  index = (index + 1) % total;
  latestSlider.style.transform = `translateX(-${index * 100}%)`;
}, 5000);

// Trending Post Slider
const trendingSlider = document.getElementById('trending-slider');

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

// Toggle-Publish
function togglePublish(id) {
  fetch(`/admin/toggle_publish/${id}`, { method: "POST" })
    .then(res => res.json())
    .then(data => {
      const badge = document.getElementById(`status-${id}`);
      badge.textContent = data.status === "published" ? "Published" : "Draft";
      badge.className = data.status === "published"
        ? "px-2 py-1 text-xs rounded bg-green-100 text-green-700"
        : "px-2 py-1 text-xs rounded bg-gray-100 text-gray-600";
    });
}
