// static/js/editor/submit.js

import { uploadImagesBeforeSave } from "./media.js";
import { updateHiddenInput } from "./helper.js";

/**
 * Handles manual "Save Draft" submission.
 *
 * Important:
 * - Uses FormData(form), so ALL named form fields are included.
 * - Includes Tribe fields.
 * - Includes category.
 * - Includes labels.
 * - Includes featured image.
 * - Includes post_id.
 * - Includes CSRF token.
 *
 * @param {HTMLElement} editor
 * @param {HTMLFormElement} form
 */
export function initSubmit(editor, form) {
  if (!editor || !form) return;

  const contentInput = document.getElementById("content-hidden");
  const draftBtn = document.getElementById("draftBtn");

  if (!contentInput || !draftBtn) return;

  // Ensure post_id input exists
  let postIdInput = form.querySelector('[name="post_id"]');

  if (!postIdInput) {
    postIdInput = document.createElement("input");
    postIdInput.type = "hidden";
    postIdInput.name = "post_id";
    form.appendChild(postIdInput);
  }

  function resetButton() {
    draftBtn.textContent = "Save Draft";
    draftBtn.disabled = false;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Prevent duplicate submissions
    if (form.dataset.submitting === "true") {
      return;
    }

    form.dataset.submitting = "true";

    draftBtn.textContent = "Saving...";
    draftBtn.disabled = true;

    try {
      await uploadImagesBeforeSave(
        editor,
        form.querySelector('[name="featured_image"]')
      );

      const content = editor.innerHTML.trim();

      if (!content) {
        throw new Error("Post content cannot be empty.");
      }

      contentInput.value = content;

      const tagsHidden = document.getElementById("tags-hidden");

      if (tagsHidden) {
        updateHiddenInput(
          tagsHidden,
          window.selectedTags || []
        );
      }

      const data = new FormData(form);

      // Make absolutely sure the editor content is current
      data.set("content", content);

      // Make sure status is draft
      data.set("status", "draft");

      // Make sure post_id is included
      data.set("post_id", postIdInput.value || "");

      // ------------------------------------
      // Debug information
      // ------------------------------------
      console.log("========== MANUAL SAVE ==========");

      console.log("Title:", data.get("title"));
      console.log("Category:", data.get("category"));

      console.log(
        "Labels:",
        data.getAll("labels")
      );

      console.log(
        "Tribe URL:",
        data.get("tribe_url")
      );

      console.log(
        "Tribe Title:",
        data.get("tribe_title")
      );

      console.log(
        "Tribe Description:",
        data.get("tribe_description")
      );

      console.log(
        "Tribe Button:",
        data.get("tribe_button_text")
      );

      console.log(
        "Post ID:",
        data.get("post_id")
      );

      // ------------------------------------
      // Send to draft endpoint
      // ------------------------------------
      const res = await fetch("/post/draft", {
        method: "POST",
        body: data,
        credentials: "same-origin"
      });

      if (!res.ok) {
        const errorText = await res.text();

        console.error(
          "Draft save failed:",
          res.status,
          errorText
        );

        throw new Error(
          `Draft save failed (HTTP ${res.status})`
        );
      }

      const json = await res.json();

      console.log("Draft response:", json);

      if (json.post_id) {
        postIdInput.value = json.post_id;
      }

      draftBtn.textContent = "Draft Saved ✅";

      showDraftMessage(
        "Draft saved successfully."
      );

      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1000);

    } catch (err) {
      console.error(
        "Manual draft save failed:",
        err
      );

      draftBtn.textContent = "Draft ❌";

      showDraftMessage(
        err.message || "Draft save failed.",
        true
      );

    } finally {
      form.dataset.submitting = "false";

      setTimeout(() => {
        resetButton();
      }, 1500);
    }
  });
}


/**
 * Small UI message
 */
function showDraftMessage(message, isError = false) {
  const flash =
    document.getElementById("flash-messages");

  if (!flash) return;

  const div = document.createElement("div");

  div.className =
    `px-4 py-2 rounded mb-2 text-sm ${
      isError
        ? "bg-red-500/20 text-red-700"
        : "bg-green-500/20 text-green-700"
    }`;

  div.textContent = message;

  flash.appendChild(div);

  setTimeout(() => {
    div.remove();
  }, 3000);
}