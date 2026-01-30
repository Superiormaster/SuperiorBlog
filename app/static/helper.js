// helper.js

// -----------------------------
// Button helpers
// -----------------------------
export function disableButtons(buttons = []) {
  buttons.forEach((b) => {
    if (b) b.disabled = true;
  });
}

export function enableButtons(buttons = []) {
  buttons.forEach((b) => {
    if (b) b.disabled = false;
  });
}

// -----------------------------
// Tags helper
// -----------------------------
export function updateHiddenInput(hiddenInput, selectedTags = []) {
  if (!hiddenInput) return;
  hiddenInput.value = selectedTags.map((t) => t.name).join(", ");
}

// -----------------------------
// Safe focus helper
// -----------------------------
export function focusIfEmpty(input) {
  if (!input) return;
  if (!input.value.trim()) {
    input.focus();
  }
}