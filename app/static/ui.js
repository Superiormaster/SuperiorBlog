// ui.js
export function initUI() {
  const scheduleBtn = document.getElementById("scheduleBtn");
  const scheduleBox = document.getElementById("scheduleBox");
  const guidelinesBtn = document.getElementById("guidelinesBtn");
  const guidelinesModal = document.getElementById("guidelinesModal");
  const closeGuidelines = document.getElementById("closeGuidelines");
  const postStatusInput = document.getElementById("post-status");
  const titleInput = document.querySelector('input[name="title"]');

  if (scheduleBtn && scheduleBox) {
    scheduleBtn.addEventListener("click", () =>
      scheduleBox.classList.toggle("hidden")
    );
  }

  if (guidelinesBtn && guidelinesModal) {
    guidelinesBtn.addEventListener("click", () =>
      guidelinesModal.classList.remove("hidden")
    );
  }

  if (closeGuidelines && guidelinesModal) {
    closeGuidelines.addEventListener("click", () =>
      guidelinesModal.classList.add("hidden")
    );
  }

  if (postStatusInput) {
    window.setStatus = (value) => (postStatusInput.value = value);
  }

  if (titleInput && !titleInput.value.trim()) {
    titleInput.focus();
  }
}