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

// Comment 
function toggleComments() {
  const section = document.getElementById("comment-section");
  section.classList.toggle("hidden");
  section.scrollIntoView({ behavior: "smooth" });
}

const noComments = document.getElementById("no-comments");
const form = document.getElementById("comment-form");
const commentList = document.getElementById("comment-list");
const commentCount = document.getElementById("comment-count");

form.addEventListener("submit", function(e) {
  e.preventDefault();

  const formData = new FormData(this);
  const slug = "{{ post.slug }}"; // Flask template variable

  fetch(this.action, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    })
  .then(res => {
    console.log(res);
    return res.json();
  })
  .then(data => {
    console.log(data);
    const li = document.createElement("li");
    li.classList.add("mb-4", "border-b", "pb-2");
    li.innerHTML = `
      <p class="font-semibold text-xl md:text-2xl">${data.author}</p>
      <p class="text-gray-400 text-sm md:text-xl">${data.content}</p>
      <p class="text-xs text-gray-500">${data.created_at}</p>
    `;
    if (noComments) {
      noComments.remove();
    }
    commentList.appendChild(li);

    // Show section if hidden
    const section = document.getElementById("comment-section");
    if (section.classList.contains("hidden")) {
      section.classList.remove("hidden");
    }

    if (commentCount) {
      let count = parseInt(commentCount.textContent);
      commentCount.textContent = count + 1;
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