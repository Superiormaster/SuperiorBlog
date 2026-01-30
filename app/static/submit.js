// static/js/editor/submit.js
import { setSafeRedirect } from "./utils.js";
import { uploadImagesBeforeSave } from "./media.js";
import { updateHiddenInput } from "./helper.js";

export function initSubmit(editor, form) {
  const contentInput = document.getElementById("content-hidden");
  const statusInput = document.getElementById("post-status");
  const scheduledInput = document.getElementById("scheduled_at");

  const draftBtn = document.getElementById("draftBtn");
  const publishBtn = document.getElementById("publishBtn");
  const confirmScheduleBtn = document.getElementById("confirmScheduleBtn");

  const minWords = window.rules?.min_words || 150;

  if (!form || !contentInput || !statusInput) return;
  
  function resetButtons() {
    draftBtn && (draftBtn.textContent = "Save Draft", draftBtn.disabled = false);
    publishBtn && (publishBtn.textContent = "Publish", publishBtn.disabled = false);
    confirmScheduleBtn && (confirmScheduleBtn.textContent = "Confirm Schedule", confirmScheduleBtn.disabled = false);
  }
  
  // -----------------------------
  // Button clicks (SET STATUS ONLY)
  // -----------------------------
  draftBtn?.addEventListener("click", () => {
    statusInput.value = "draft";
    form.dataset.action = "draft";
    form.requestSubmit();
  });

  publishBtn?.addEventListener("click", () => {
    statusInput.value = "published";
    form.dataset.action = "publish";
    form.requestSubmit();
  });

  confirmScheduleBtn?.addEventListener("click", () => {
    if (!scheduledInput?.value) {
      showError("Please select a schedule date");
      return;
    }

    const scheduledDate = new Date(scheduledInput.value);
    const now = new Date();
    if (scheduledDate <= now) {
      showError("The selected date is not valid. It must be in the future.");
      return;
    }

    statusInput.value = "scheduled";
    form.dataset.action = "schedule";
    form.requestSubmit();
  });

  // -----------------------------
  // SINGLE submit handler
  // -----------------------------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
  
    // Prevent double submissions
    if (form.dataset.submitting === "true") return;
    form.dataset.submitting = "true";

    const action = form.dataset.action;

    try {
      setLoading(true);
  
      if (action === "draft" && draftBtn) {
        draftBtn.textContent = "Saving…";
        draftBtn.disabled = true;
      }
      
      if (action === "publish" && publishBtn) {
        publishBtn.textContent = "Publishing…";
        publishBtn.disabled = true;
      }
      
      if (action === "schedule" && confirmScheduleBtn) {
        confirmScheduleBtn.textContent = "Confirming…";
        confirmScheduleBtn.disabled = true;
      }

      if (!navigator.onLine) {
        throw new Error("Network unavailable");
      }

      await uploadImagesBeforeSave(editor);

      const content = editor.innerHTML.trim();
      const words = window.updateWordCount();

      // Validation rules
      if (statusInput.value === "published" && words < minWords) {
        throw new Error(`Minimum ${minWords} words required`);
      }

      if (statusInput.value === "scheduled" && !scheduledInput?.value) {
        throw new Error("Schedule date missing");
      }

      contentInput.value = content;
      updateHiddenInput(
        document.getElementById("tags-hidden"),
        window.selectedTags || []
      );

      form.submit();

    } catch (err) {
      showError(err.message || "Submission failed");
      if (draftBtn) {
        draftBtn.textContent = "Draft ❌";
        draftBtn.disabled = false;
      }
      setLoading(false);
    } finally {
      delete form.dataset.action;
      form.dataset.submitting = "false";
    }
  });
}