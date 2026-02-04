// autosave.js

// -----------------------------
// Auto-save draft every 10s
// -----------------------------
export function initAutoSave(editor, form) {
  window.isUploadingImages = false;

  let timer;

  editor.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (window.isUploadingImages) {
        console.log("Autosave skipped: images uploading");
        return;
      }

      const data = new FormData(form);
      data.set("content", editor.innerHTML);
      data.set("status", "draft");

      try {
        const res = await fetch("/post/draft", { method: "POST", body: data })
        // Check HTTP status first
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        // Try to parse JSON safely
        let json;
        try {
          json = await res.json();
        } catch (err) {
          console.warn("Server did not return JSON, continuing anyway", err);
          json = {};
        }

        if (json.post_id) {
          const postIdInput = form.querySelector('[name="post_id"]');
          if (postIdInput) {
            postIdInput.value = json.post_id;
          }
        }

        // Show a small confirmation for the user
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
          }, 1500); // revert after 1.5s
        }
      }
    }, 10000);
  });
}

// Optional: small UI message for auto-draft status
function showDraftSavedMessage(msg, isError = false) {
  const flash = document.getElementById("flash-messages");
  if (!flash) return;

  const div = document.createElement("div");
  div.className = `px-4 py-2 rounded mb-2 text-sm transition ${
    isError ? "bg-red-500/20 text-red-700" : "bg-green-500/20 text-green-700"
  }`;
  div.textContent = msg;

  flash.appendChild(div);

  // Remove after 3 seconds
  setTimeout(() => div.remove(), 3000);
}