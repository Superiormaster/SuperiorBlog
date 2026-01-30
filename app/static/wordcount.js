// wordcount.js

// Update word count
export function initWordCount(editor) {
  const display = document.getElementById("word-count");
  const minWords = window.rules?.min_words || 150;

  window.updateWordCount = () => {
    const temp = document.createElement("div");
    temp.innerHTML = editor.innerHTML;
    const text = temp.innerText.trim();
    let count = text ? text.split(/\s+/).length : 0;
    count += temp.querySelectorAll("img, iframe").length;

    if (display) {
      display.textContent = `Word count: ${count} (min ${minWords})`;
    }

    return count;
  };

  editor.addEventListener("input", window.updateWordCount);
  window.updateWordCount();
}