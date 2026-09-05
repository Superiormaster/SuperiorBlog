// static/js/editor/autosave.js

import { uploadImagesBeforeSave } from "./media.js";

/**
 * Auto-save draft every 10 seconds after editor changes.
 *
 * @param {HTMLElement} editor
 * @param {HTMLFormElement} form
 */
export function initAutoSave(editor, form) {
  if (!editor || !form) return;

  const draftBtn =
    document.getElementById("draftBtn");

  let postIdInput =
    form.querySelector('[name="post_id"]');

  if (!postIdInput) {
    postIdInput = document.createElement("input");

    postIdInput.type = "hidden";
    postIdInput.name = "post_id";
    postIdInput.value = "";

    form.appendChild(postIdInput);
  }

  window.isUploadingImages = false;

  let timer = null;

  /**
   * Perform the actual autosave.
   */
  async function saveDraftAutomatically() {
    postIdInput =
      form.querySelector('[name="post_id"]');

    const content =
      editor.innerHTML.trim();

    if (!content) {
      console.log(
        "Autosave skipped: no content"
      );
      return;
    }

    if (window.isUploadingImages) {
      console.log(
        "Autosave skipped: images uploading"
      );
      return;
    }

    try {
      await uploadImagesBeforeSave(
        editor,
        form.querySelector(
          '[name="featured_image"]'
        )
      );

      const data = new FormData(form);

      // Always use latest editor content
      data.set(
        "content",
        editor.innerHTML
      );

      data.set(
        "title",
        form.title?.value ||
        "Untitled Draft"
      );

      data.set(
        "status",
        "draft"
      );

      data.set(
        "post_id",
        postIdInput.value || ""
      );

      const tribeUrl =
        form.querySelector(
          '[name="tribe_url"]'
        );

      const tribeTitle =
        form.querySelector(
          '[name="tribe_title"]'
        );

      const tribeDescription =
        form.querySelector(
          '[name="tribe_description"]'
        );

      const tribeButton =
        form.querySelector(
          '[name="tribe_button_text"]'
        );

      data.set(
        "tribe_url",
        tribeUrl?.value?.trim() || ""
      );

      data.set(
        "tribe_title",
        tribeTitle?.value?.trim() || ""
      );

      data.set(
        "tribe_description",
        tribeDescription?.value?.trim() || ""
      );

      data.set(
        "tribe_button_text",
        tribeButton?.value?.trim() || ""
      );

      console.log(
        "========== AUTO SAVE =========="
      );

      console.log(
        "Title:",
        data.get("title")
      );

      console.log(
        "Category:",
        data.get("category")
      );

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

      const res = await fetch(
        "/post/draft",
        {
          method: "POST",
          body: data,
          credentials: "same-origin"
        }
      );

      if (!res.ok) {
        const errorText =
          await res.text();

        console.error(
          "Server returned:",
          res.status,
          errorText
        );

        throw new Error(
          `HTTP ${res.status}`
        );
      }

      const json =
        await res.json();

      console.log(
        "Autosave response:",
        json
      );

      if (json.post_id) {
        postIdInput.value =
          json.post_id;
      }

      if (
        json.status === "saved" ||
        json.status === "updated"
      ) {
        if (draftBtn) {
          draftBtn.textContent =
            "Draft Saved ✅";
        }

        showDraftSavedMessage(
          "Draft saved successfully."
        );
      }

    } catch (err) {
      console.error(
        "Auto-draft failed:",
        err
      );

      if (draftBtn) {
        draftBtn.textContent =
          "Draft ❌";
      }

      showDraftSavedMessage(
        "Auto-draft failed.",
        true
      );

    } finally {
      if (draftBtn) {
        setTimeout(() => {
          draftBtn.textContent =
            "Save Draft";

          draftBtn.disabled =
            false;
        }, 1500);
      }
    }
  }

  editor.addEventListener(
    "input",
    () => {
      clearTimeout(timer);

      timer = setTimeout(
        saveDraftAutomatically,
        10000
      );
    }
  );

  [
    "tribe_url",
    "tribe_title",
    "tribe_description",
    "tribe_button_text"
  ].forEach((fieldName) => {
    const field =
      form.querySelector(
        `[name="${fieldName}"]`
      );

    if (!field) return;

    field.addEventListener(
      "input",
      () => {
        clearTimeout(timer);

        timer = setTimeout(
          saveDraftAutomatically,
          10000
        );
      }
    );
  });
}


/**
 * Display autosave status message.
 */
function showDraftSavedMessage(
  msg,
  isError = false
) {
  const flash =
    document.getElementById(
      "flash-messages"
    );

  if (!flash) return;

  const div =
    document.createElement("div");

  div.className =
    `px-4 py-2 rounded mb-2 text-sm transition ${
      isError
        ? "bg-red-500/20 text-red-700"
        : "bg-green-500/20 text-green-700"
    }`;

  div.textContent = msg;

  flash.appendChild(div);

  setTimeout(() => {
    div.remove();
  }, 3000);
}