// toolbar.js

export function initToolbar(editor) {
  if (!editor) return;

  function activate(cmd) {
    document.querySelector(`.format-btn[data-cmd="${cmd}"]`)
      ?.classList.add("active");
  }

  function syncToolbar() {
    const selection = window.getSelection();
    if (!selection.rangeCount) return;

    let node = selection.anchorNode;
    if (node.nodeType === 3) node = node.parentNode;

    document.querySelectorAll(".format-btn").forEach(btn => btn.classList.remove("active"));

    ["bold", "italic"].forEach(cmd => {
      try {
        if (document.queryCommandState(cmd)) 
        activate(cmd);
      } catch {}
    });

    let el = node;
    while (el && el !== editor) {
      if (el.tagName === "H1") {
        activate("h1");
        break;
      }
      if (el.tagName === "H2") {
        activate("h2");
        break;
      }
      el = el.parentNode;
    }
    
        // LINK
    el = node;
    while (el && el !== editor) {
      if (el.tagName === "A") {
        activate("createLink");
        break;
      }
      el = el.parentNode;
    }
  }

  function pulse(btn) {
    btn.classList.add("active");
    setTimeout(() => btn.classList.remove("active"), 150);
  }
  
  document.querySelectorAll("#toolbar button").forEach(btn => {
    btn.addEventListener("mousedown", e => e.preventDefault());
    btn.addEventListener("click", () => {
      const cmd = btn.dataset.cmd;
      if (!cmd) return;

      editor.focus();

      if (["undo", "redo"].includes(cmd)) { document.execCommand(cmd); pulse(btn); return; }

      if (cmd === "h1" || cmd === "h2") {
        const isActive = btn.classList.contains("active");
        document.execCommand("formatBlock", false, isActive ? "p" : cmd);
        syncToolbar();
        return;
      }

      if (cmd === "bold" || cmd === "italic") {
        document.execCommand(cmd, false, null);
      }

      if (cmd === "createLink") {
        const url = prompt("Enter URL:");
        if (!url) return;
        if (window.getSelection().isCollapsed) {
          const a = document.createElement("a");
          a.href = url; a.textContent = url;
          window.getSelection().getRangeAt(0).insertNode(a);
          // move cursor after link
          const range = document.createRange();
          range.setStartAfter(a);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
        } else {
          document.execCommand("createLink", false, url);
        }
      }

      syncToolbar();
    });
  });

  editor.addEventListener("keyup", syncToolbar);
  editor.addEventListener("mouseup", syncToolbar);
  editor.addEventListener("focus", syncToolbar);
  document.addEventListener("selectionchange", () => { if (document.activeElement === editor) syncToolbar(); });
}