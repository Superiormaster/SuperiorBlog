// GLOBAL HELPERS

function disable(el, text = "Loading...") {
  el.dataset.originalText = el.innerHTML;
  el.innerHTML = text;
  el.disabled = true;
  el.classList.add("opacity-50", "cursor-not-allowed");
}

function enable(el) {
  el.innerHTML = el.dataset.originalText;
  el.disabled = false;
  el.classList.remove("opacity-50", "cursor-not-allowed");
}

function showError(container, message) {
  container.innerHTML = `
    <div class="text-sm text-red-600 mt-2">${message}</div>
  `;
}

// --------- CONFIG ---------
const POST_ID = 1; // replace dynamically
let commentOffset = 0;
const COMMENT_LIMIT = 5;

// COMMENT FORM

document.getElementById("commentForm").addEventListener("submit", async e => {
  e.preventDefault();

  const btn = document.getElementById("commentBtn");
  const input = document.getElementById("commentInput");
  const errorBox = document.getElementById("commentError");

  if (!input.value.trim()) {
    showError(errorBox, "Comment cannot be empty");
    return;
  }

  disable(btn);

  try {
    const res = await fetch("/comments/create", {
      method: "POST",
      body: new URLSearchParams({
        post_id: POST_ID,
        content: input.value
      })
    });

    const data = await res.json();

    if (!res.ok) throw new Error(data.error);

    input.value = "";
    errorBox.innerHTML = "";

    loadComments(true); // refresh comments
  } catch (err) {
    showError(errorBox, err.message || "Something went wrong");
  } finally {
    enable(btn);
  }
});

// LOAD COMMENTS

async function loadComments(reset = false) {
  const btn = document.getElementById("loadMoreComments");

  if (reset) {
    commentOffset = 0;
    document.getElementById("comments").innerHTML = "";
  }

  disable(btn, "Loading...");

  try {
    const res = await fetch(
      `/comments/${POST_ID}?limit=${COMMENT_LIMIT}&offset=${commentOffset}`
    );

    const data = await res.json();

    if (data.length === 0) {
      btn.style.display = "none";
      return;
    }

    data.forEach(renderComment);

    commentOffset += COMMENT_LIMIT;
  } catch {
    btn.innerHTML = "Failed to load";
  } finally {
    enable(btn);
  }
}

document.getElementById("loadMoreComments")
  .addEventListener("click", () => loadComments());

// REPLY BUTTON

function renderComment(c) {
  const div = document.createElement("div");
  div.className = "border-b py-3 border rounded-lg p-3 bg-gray-50 shadow-sm comment";

  div.innerHTML = `
    <div class="flex items-start space-x-2">
      <img src="https://via.placeholder.com/40" class="w-10 h-10 rounded-full" alt="Avatar">
      <div class="flex-1">
        <div class="flex justify-between">
          <p class="text-sm font-semibold">${c.user}</p>
          <button class="text-xs text-gray-500 hover:underline" onclick="deleteComment(${c.id}, this)">Delete</button>
        </div>
        <p class="text-sm mt-1">${c.content}</p>
  
        <button class="text-xs text-blue-600 mt-1"
          onclick="loadReplies(${c.id}, this)">
          View replies (${c.replies_count})
        </button>
  
        <div id="replies-${c.id}" class="ml-4 mt-2 space-y-2"></div>
      </div>
    </div>
  `;

  document.getElementById("comments").appendChild(div);
}

// LOAD REPLY

async function loadReplies(commentId, btn) {
  const container = document.getElementById(`replies-${commentId}`);
  let offset = container.children.length;

  disable(btn, "Loading...");

  try {
    const res = await fetch(
      `/comments/replies/${commentId}?limit=2&offset=${offset}`
    );

    const data = await res.json();

    if (data.length === 0) {
      btn.style.display = "none";
      return;
    }

    data.forEach(r => {
      const div = document.createElement("div");
      div.className = "text-sm mt-1 flex items-start space-x-2";
      div.innerHTML = `
        <img src="https://via.placeholder.com/30" class="w-7 h-7 rounded-full" alt="Avatar">
        <div>
          <p class="text-sm font-semibold">${r.user}</p>
          <p class="text-sm">${r.content}</p>
        </div>
      `;
      container.appendChild(div);
    });
  } catch {
    btn.innerHTML = "Retry";
  } finally {
    enable(btn);
  }
}

// DELETE COMMENT
async function deleteComment(id, btn) {
  if (!confirm("Delete this comment?")) return;

  disable(btn, "Deleting...");

  try {
    const res = await fetch(`/comments/delete/${id}`, { method: "POST" });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error);

    btn.closest(".comment").remove();
  } catch {
    btn.innerHTML = "Failed";
  }
}

// --------- INITIAL LOAD ---------
loadComments();

// REACTION
async function react(btn, commentId) {
  const reactionType = btn.dataset.reaction;
  disable(btn, "...");
  try {
    const res = await fetch(`/comments/react/${commentId}`, {
      method: "POST",
      body: new URLSearchParams({ reaction: reactionType })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    // Update counts
    const countSpan = document.getElementById(`reaction-count-${commentId}`);
    const total = Object.values(data.counts).reduce((a,b) => a+b, 0);
    countSpan.textContent = `${total} reactions`;

    // Highlight selected reaction
    btn.parentNode.querySelectorAll(".reaction-btn").forEach(b=>{
      b.classList.remove("bg-blue-100", "text-blue-600");
    });
    btn.classList.add("bg-blue-100", "text-blue-600");
  } catch(err) {
    alert(err.message || "Reaction failed");
  } finally {
    enable(btn);
  }
}