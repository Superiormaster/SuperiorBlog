// -----------------------------
// GLOBAL FUNCTIONS
// -----------------------------
function toggleComments() {
  const section = document.getElementById("comment-section");
  section.classList.toggle("hidden");

  // Show fixed comment form when section opens
  const form = document.getElementById("fixed-comment-form");
  if (!section.classList.contains("hidden") && form) {
    form.classList.remove("hidden");
  }
}

function toggleReplies(commentId) {
  const replies = document.getElementById(`replies-${commentId}`);
  const btn = document.getElementById(`toggle-replies-btn-${commentId}`);
  if (!replies || !btn) return;

  if (replies.classList.contains("hidden")) {
    replies.classList.remove("hidden");
    btn.textContent = "Hide Replies";
  } else {
    replies.classList.add("hidden");
    btn.textContent = `View Replies (${replies.children.length})`;
  }
}

function toggleReplyForm(commentId) {
  const form = document.getElementById(`reply-form-${commentId}`);
  if (!form) return;
  const textarea = form.querySelector("textarea");

  form.classList.toggle("hidden");

  if (!form.classList.contains("hidden")) {
    textarea.value = "";
    textarea.focus();
  }
}

function closeCommentForm() {
  const form = document.getElementById("fixed-comment-form");
  if (form) form.classList.add("hidden");
}

// Make global for inline onclick fallback (optional)
window.toggleComments = toggleComments;
window.toggleReplies = toggleReplies;
window.toggleReplyForm = toggleReplyForm;
window.closeCommentForm = closeCommentForm;

// -----------------------------
// FIXED COMMENT FORM (BOTTOM)
// -----------------------------
const commentForm = document.getElementById("fixed-comment-form");
if (commentForm) {
  const commentTextarea = commentForm.querySelector("textarea");

  commentTextarea.addEventListener("focus", () => {
    commentForm.classList.remove("hidden"); // show form
  });

  commentForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const textarea = this.querySelector("textarea");
    const formData = new FormData(this);
    const commentList = document.getElementById("comment-list");
    const commentCount = document.getElementById("comment-count");
    const noComments = document.getElementById("no-comment");

    fetch(this.action, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .then(res => res.json())
      .then(data => {
        const li = document.createElement("li");
        li.classList.add("mb-4", "border-b", "pb-2");
        li.innerHTML = `
          <p class="font-semibold text-xl md:text-2xl">${data.username}</p>
          <p class="text-gray-400 text-sm md:text-xl">${data.content}</p>
          <p class="text-xs text-gray-500">${data.created_at}</p>
          <div class="flex gap-3 mt-2">
            <button data-reply-btn data-comment-id="${data.comment_id}" class="btn-primary text-blue-500 text-sm">
              Reply
            </button>
            <button data-toggle-replies-btn data-comment-id="${data.comment_id}" class="btn-primary text-gray-500 text-sm hidden" id="toggle-replies-btn-${data.comment_id}">
              View Replies (0)
            </button>
          </div>
          <form id="reply-form-${data.comment_id}" action="${data.reply_url}" method="POST" class="mt-2 ml-4 hidden">
            <input type="hidden" name="csrf_token" value="${data.csrf_token}">
            <textarea name="content" placeholder="Write a reply..." class="border rounded px-2 py-1 w-full text-sm" required></textarea>
            <button type="submit" class="btn-primary bg-blue-600 text-white px-2 py-1 rounded text-sm mt-1">
              <i class="fas fa-paper-plane"></i>
            </button>
          </form>
          <ul id="replies-${data.comment_id}" class="ml-6 mt-3 hidden"></ul>
        `;

        if (noComments) noComments.remove();
        commentList.prepend(li); // Add on top

        textarea.value = ""; // clear textarea
        if (commentCount) commentCount.textContent = parseInt(commentCount.textContent) + 1;

        attachReplySubmit(li.querySelector("form")); // Attach reply handler
      })
      .catch(err => console.error(err));
  });
}

// -----------------------------
// REPLY HANDLER
// -----------------------------
function attachReplySubmit(form) {
  if (!form) return;
  form.addEventListener("submit", function (e) {
    e.preventDefault();

    const textarea = this.querySelector("textarea");
    const formData = new FormData(this);
    const repliesList = this.closest("li").querySelector("ul[id^='replies-']");

    fetch(this.action, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .then(res => res.json())
      .then(data => {
        const li = document.createElement("li");
        li.classList.add("border-l-2", "border-gray-600", "pl-3", "mb-2");
        li.innerHTML = `
          <p class="font-semibold text-sm">${data.username}</p>
          <p class="text-gray-400 text-sm">${data.content}</p>
          <p class="text-xs text-gray-500">${data.created_at}</p>
        `;
        repliesList.prepend(li); // Add reply on top
        repliesList.classList.remove("hidden");

        textarea.value = ""; // clear
        textarea.focus();   // focus but don't scroll
      })
      .catch(err => console.error(err));
  });
}

// Attach reply handler for existing replies on page load
document.querySelectorAll("[id^='reply-form-']").forEach(form => attachReplySubmit(form));

// -----------------------------
// EVENT DELEGATION FOR DYNAMIC BUTTONS
// -----------------------------
document.addEventListener("click", function (e) {
  const replyBtn = e.target.closest("[data-reply-btn]");
  if (replyBtn) {
    toggleReplyForm(replyBtn.dataset.commentId);
  }

  const toggleBtn = e.target.closest("[data-toggle-replies-btn]");
  if (toggleBtn) {
    toggleReplies(toggleBtn.dataset.commentId);
  }
});