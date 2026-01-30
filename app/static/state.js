// static/js/editor/state.js

export const state = {
  loading: false,
};

export function initState() {
  window.setLoading = (value = true) => {
    state.loading = value;

    document
      .querySelectorAll("button")
      .forEach((btn) => (btn.disabled = value));
  };

  window.showError = (msg) => {
    const box = document.getElementById("flash-messages");
    if (!box) return alert(msg);

    const div = document.createElement("div");
    div.className =
      "bg-red-500/10 text-red-400 px-4 py-2 rounded mb-2";
    div.textContent = msg;

    box.appendChild(div);
    setTimeout(() => div.remove(), 4000);
  };
}