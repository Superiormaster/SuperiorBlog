// autosave.js

import { uploadImagesBeforeSave } from "./media.js";

// -----------------------------
// Auto-save draft every 10s
// -----------------------------
export function initAutoSave(editor, form) {
  const draftBtn = document.getElementById("draftBtn");
  let postIdInput = form.querySelector('[name="post_id"]');

  if (!postIdInput) {
    // Dynamically create hidden post_id input if missing
    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = "post_id";
    form.appendChild(hidden);
    postIdInput = hidden;
  }

  window.isUploadingImages = false;

  let timer;

  editor.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      postIdInput = form.querySelector('[name="post_id"]');
      const content = editor.innerHTML.trim();
      if (!content) return;

      if (window.isUploadingImages) {
        console.log("Autosave skipped: images uploading");
        return;
      }

      try {
        // -----------------------------
        // Upload images first
        // -----------------------------
        await uploadImagesBeforeSave(editor, form.querySelector('[name="featured_image"]'));

        // -----------------------------
        // Prepare form data
        // -----------------------------
        const updatedContent = editor.innerHTML;
        postIdInput = form.querySelector('[name="post_id"]');

        const data = new FormData(form);
        data.set("content", updatedContent);
        data.set("title", form.title?.value || "Untitled Draft");
        data.set("status", "draft");
        data.set("post_id", postIdInput.value || "");

        // -----------------------------
        // Send to backend with credentials
        // -----------------------------
        const res = await fetch("/post/draft", {
          method: "POST",
          body: data,
          credentials: "same-origin", // ✅ ensure cookies/session are sent
        });

        if (!res.ok) {
          console.error("Server returned error", res.status, await res.text());
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        let json;
        try {
          json = await res.json();
        } catch (err) {
          console.warn("Server did not return JSON, continuing anyway", err);
          json = {};
        }

        // Update post_id if backend returned one
        if (json.post_id) {
          postIdInput.value = json.post_id;
        }

        // UI feedback
        if (json.status === "saved" || json.status === "updated") {
          if (draftBtn) draftBtn.textContent = "Draft Saved ✅";
          showDraftSavedMessage(`Draft ${json.status} successfully`);
        } else if (json.status === "ignored") {
          if (draftBtn) draftBtn.textContent = "Draft";
          console.log("No content to save, draft ignored");
        }

      } catch (err) {
        if (draftBtn) draftBtn.textContent = "Draft ❌";
        console.error("Auto-draft failed:", err);
        showDraftSavedMessage("Auto-draft failed", true);
      } finally {
        if (draftBtn) {
          setTimeout(() => {
            draftBtn.textContent = "Draft";
            draftBtn.disabled = false;
          }, 1500);
        }
      }
    }, 10000); // debounce 10s
  });
}

// -----------------------------
// Optional: small UI message for auto-draft status
// -----------------------------
function showDraftSavedMessage(msg, isError = false) {
  const flash = document.getElementById("flash-messages");
  if (!flash) return;

  const div = document.createElement("div");
  div.className = `px-4 py-2 rounded mb-2 text-sm transition ${
    isError ? "bg-red-500/20 text-red-700" : "bg-green-500/20 text-green-700"
  }`;
  div.textContent = msg;

  flash.appendChild(div);

  setTimeout(() => div.remove(), 3000);
}