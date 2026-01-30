// tags.js

export function initTags(tagInput, suggestionsBox, selectedTagsBox, hiddenInput, MAX_TAGS = 5, existingTags = []) {
  if (!tagInput || !suggestionsBox || !selectedTagsBox || !hiddenInput) return;

  window.selectedTags = [];

  function updateHiddenInput() { hiddenInput.value = window.selectedTags.map(t => t.name).join(", "); }
  function updateVisibleInput() { tagInput.value = window.selectedTags.map(t => t.name).join(", "); }

  function createChip(tag) {
    const chip = document.createElement("span");
    chip.className = "bg-blue-600 text-white px-3 py-1 rounded-full text-sm flex items-center gap-2";
    chip.innerHTML = `${tag.name} <button type="button">&times;</button>`;
    chip.querySelector("button").onclick = () => {
      window.selectedTags = window.selectedTags.filter(t => t.name !== tag.name);
      chip.remove();
      updateHiddenInput(); updateVisibleInput();
    };
    selectedTagsBox.appendChild(chip);
  }

  function addTag(tag) {
    tag = { name: tag.name.trim() }; if (!tag.name) return;
    if (window.selectedTags.some(t => t.name.toLowerCase() === tag.name.toLowerCase())) return;
    if (window.selectedTags.length >= MAX_TAGS) { alert(`Max ${MAX_TAGS} tags allowed`); return; }
    window.selectedTags.push(tag); createChip(tag); updateHiddenInput(); updateVisibleInput();
  }

  async function fetchTags(query) {
    const res = await fetch(`/admin/tags/search?q=${encodeURIComponent(query)}`);
    const tags = await res.json();
    suggestionsBox.innerHTML = "";
    tags.forEach(tag => {
      const item = document.createElement("div");
      item.className = "px-3 py-2 cursor-pointer hover:bg-gray-700";
      item.textContent = tag.name;
      item.onclick = () => {
        addTag({ name: tag.name });
        tagInput.value = window.selectedTags.map((t) => t.name).join(", ") + ", ";
        suggestionsBox.classList.add("hidden");
      };
      suggestionsBox.appendChild(item);
    });
    suggestionsBox.classList.toggle("hidden", tags.length === 0);
  }

  tagInput.addEventListener("input", () => {
    const val = tagInput.value.split(",").pop().trim();
    if (!val) return suggestionsBox.classList.add("hidden");
    fetchTags(val);
  });

  tagInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); 
      const parts = tagInput.value.split(",");
      const lastTag = parts[parts.length - 1].trim();
      if (!lastTag) return;
      addTag({ name: lastTag });
      tagInput.value = window.selectedTags.map((t) => t.name).join(", ") + ", ";
      suggestionsBox.classList.add("hidden"); }
  });

  if (window.existingTags && Array.isArray(window.existingTags)) {
    window.existingTags.forEach((name) => addTag({ name }));
  }
  if (form) form.addEventListener("submit", updateHiddenInput);
}