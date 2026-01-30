// static/js/editor/main.js
import { initToolbar } from "./toolbar.js";
import { initMedia, uploadImagesBeforeSave, insertVideo } from "./media.js";
import { initTags } from "./tags.js";
import { initState } from "./state.js";
import { initWordCount } from "./wordcount.js";
import { initAutoSave } from "./autosave.js";
import { setSafeRedirect } from "./utils.js";
import { updateHiddenInput, disableButtons, enableButtons, focusIfEmpty } from "./helper.js";
import { initUI } from "./ui.js";
import { initSubmit } from "./submit.js";

document.addEventListener("DOMContentLoaded", () => {
  const editor = document.getElementById("editor");
  const form = document.getElementById("post-form");
  const wordCountDisplay = document.getElementById("word-count");
  const minWords = window.rules?.min_words || 150;

  // Tag elements
  const tagInput = document.getElementById("tag-input");
  const suggestionsBox = document.getElementById("tag-suggestions");
  const selectedTagsBox = document.getElementById("selected-tags");
  const hiddenTagsInput = document.getElementById("tags-hidden");

  // Media elements
  const insertImageBtn = document.getElementById("insertImageBtn");
  const uploader = document.getElementById("imageUploader");

  if (!editor || !form) return; // Not on editor page

  // Initialize all modules
  initState();
  initToolbar(editor);
  initWordCount(editor, wordCountDisplay, minWords);
  initMedia(editor, insertImageBtn, uploader, wordCountDisplay, minWords);
  initUI();
  initAutoSave(editor, form);
  initSubmit(editor, form);
  initTags({
    tagInput,
    suggestionsBox,
    selectedTagsBox,
    hiddenInput: hiddenTagsInput,
    form,
    MAX_TAGS: 5,
    existingTags: window.existingTags || []
  });

  // Optional: update word count on editor input
  editor.addEventListener("input", () => updateWordCount(editor, wordCountDisplay, minWords));
});