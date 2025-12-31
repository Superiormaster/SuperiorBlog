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

function likePost(postId) {
  // Prevent multiple clicks
  if (likedPosts.has(postId)) return;

  const likeBtn = document.getElementById(`like-btn-${postId}`);
  const likeCount = document.getElementById(`like-count-${postId}`);

  // Optimistic UI: increment immediately
  likeCount.textContent = parseInt(likeCount.textContent) + 1;
  likedPosts.add(postId);

  // Animate button
  likeBtn.classList.add('animate-bounce');
  setTimeout(() => likeBtn.classList.remove('animate-bounce'), 500);

  // Send like to server
  fetch(`/post/${postId}/like`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      // Ensure server count is synced
      likeCount.textContent = data.count;
      if (!data.liked) {
        // If already liked on server, don't allow multiple
        likedPosts.delete(postId);
      }
    })
    .catch(() => {
      // Revert in case of network error
      likeCount.textContent = parseInt(likeCount.textContent) - 1;
      likedPosts.delete(postId);
    });
}

// Comment 
function toggleComments() {
  const section = document.getElementById("comment-section");
  section.classList.toggle("hidden");
  section.scrollIntoView({ behavior: "smooth" });
}

const form = document.getElementById("comment-form");
const commentList = document.getElementById("comment-list");

form.addEventListener("submit", function(e) {
  e.preventDefault();

  const formData = new FormData(form);
  const slug = "{{ post.slug }}"; // Flask template variable

  fetch(`/post/${slug}/comment`, {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    const li = document.createElement("li");
    li.classList.add("mb-4", "border-b", "pb-2");
    li.innerHTML = `
      <p class="font-semibold text-xl md:text-2xl">${data.author}</p>
      <p class="text-gray-400 text-sm md:text-xl">${data.content}</p>
      <p class="text-xs text-gray-500">Just now</p>
    `;
    commentList.appendChild(li);

    // Show section if hidden
    const section = document.getElementById("comment-section");
    if (section.classList.contains("hidden")) {
      section.classList.remove("hidden");
    }

    form.reset();
    li.scrollIntoView({ behavior: "smooth" });
  })
  .catch(err => console.error(err));
});

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
