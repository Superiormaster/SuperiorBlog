// media.js
import { initWordCount } from "./wordcount.js";

/**
 * Initialize media handling for editor
 * @param {HTMLElement} editor - contenteditable editor
 * @param {HTMLElement} insertImageBtn - button to insert image
 * @param {HTMLInputElement} uploader - hidden file input
 * @param {HTMLElement} wordCountDisplay - element to show word count
 * @param {number} minWords - minimum word requirement
 */

export function initMedia(editor, insertImageBtn, uploader, display, minWords) {
  if (!editor || !insertImageBtn || !uploader) return;

  // -----------------------------
  // Image insertion
  // -----------------------------
  insertImageBtn.addEventListener("click", () => {
    // 1️⃣ Change button background while clicked
    insertImageBtn.classList.add("bg-blue-500", "text-white"); // Tailwind example
    setTimeout(() => insertImageBtn.classList.remove("bg-blue-500", "text-white"), 200); // revert after 200ms
  
    // 2️⃣ Open file picker
    uploader.click();
  });

  // Handle file selection and upload
  uploader.addEventListener("change", async () => {
    const file = uploader.files[0];
    if (!file) return;
  
    const existingImages = editor.querySelectorAll("img");
    if (existingImages.length >= 1) {
      alert("Only one image is allowed.");
      uploader.value = "";
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.createElement("img");
      img.src = e.target.result; 
      img.classList.add("rounded", "mt-1", "mb-4");

      const sel = window.getSelection();
      if (!sel.rangeCount) {
        editor.appendChild(img);
      } else {
        const range = sel.getRangeAt(0);
        range.deleteContents();
        range.insertNode(img);
    
        range.setStartAfter(img);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
      }
      initWordCount(editor, display, minWords);
    };
    reader.readAsDataURL(file);

    uploader.value = "";
  });
}

  // -----------------------------
  // Insert video
  // -----------------------------
  export function insertVideo(editor, display, minWords) {
    const url = prompt("Enter video URL (YouTube/Vimeo):");
    if (url) {
      const iframe = document.createElement("iframe");
      iframe.src = url;
      iframe.width = "560";
      iframe.height = "315";
      iframe.setAttribute("frameborder", "0");
      iframe.setAttribute("allowfullscreen", true);
      editor.appendChild(iframe);
      initWordCount(editor, display, minWords);
    }
  };

/**
 * Upload images in editor before submission
 * @param {HTMLElement} editor - contenteditable editor
 * @param {HTMLInputElement} [featuredInput] - optional featured image input
 */
 // media.js
window.isUploadingImages = false;

export async function uploadImagesBeforeSave(editor, featuredInput) {
  window.isUploadingImages = true;
  
  try {
    const images = editor.querySelectorAll("img");
    if (images.length > 1) {
      alert("Only one image is allowed for now.");
      throw new Error("Image limit exceeded");
    }
  
    featuredInput = featuredInput || document.getElementById("featured_image");
  
    let featuredSet = featuredInput && featuredInput.value;
  
    for (const img of images) {
      if (!img.src.startsWith("data:")) continue;
      const blob = await fetch(img.src).then(r => r.blob());
      const formData = new FormData();
      formData.append("image", blob, "editor-image.png");
  
      const res = await fetch("/public/upload-image", { method: "POST", body: formData });
      if (!res.ok) {
        alert("Image upload failed");
        throw new Error("Upload failed");
      }
  
      const data = await res.json();
    
      if (!data.location) {
        alert("Invalid upload response");
        throw new Error("Invalid response");
      }
  
      // ✅ Replace base64 with Cloudinary URL
      img.src = data.location;
      if (!featuredSet && featuredInput) {
        featuredInput.value = data.location;
        featuredSet = true;
      }
    }
  } finally {
    window.isUploadingImages = false;
  }
}