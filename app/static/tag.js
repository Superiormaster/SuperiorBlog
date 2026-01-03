document.addEventListener("DOMContentLoaded", () => {
  const tagInput = document.getElementById("tag-input");
  const suggestionsBox = document.getElementById("tag-suggestions");
  const selectedTagsBox = document.getElementById("selected-tags");
  const hiddenInput = document.getElementById("tags-hidden");
  const form = document.getElementById("post-form");

  if (!tagInput || !suggestionsBox || !selectedTagsBox || !hiddenInput || !form) return;

  const MAX_TAGS = 5;
  let selectedTags = [];

  function updateHiddenInput() {
    hiddenInput.value = selectedTags.map(t => t.name).join(", ");
  }
  function updateVisibleInput() {
    tagInput.value = selectedTags.map(t => t.name).join(", ");
  }

  function createChip(tag) {
    const chip = document.createElement("span");
    chip.className = "bg-blue-600 text-white px-3 py-1 rounded-full text-sm flex items-center gap-2";
    chip.innerHTML = `${tag.name} <button type="button">&times;</button>`;

    chip.querySelector("button").onclick = () => {
      selectedTags = selectedTags.filter(t => t.name !== tag.name);
      chip.remove();
      updateHiddenInput();
      updateVisibleInput();
    };

    selectedTagsBox.appendChild(chip);
  }

  function addTag(tag) {
    tag = { name: tag.name.trim() };
    if (!tag.name) return;
    if (selectedTags.some(t => t.name.toLowerCase() === tag.name.toLowerCase())) return;
    if (selectedTags.length >= MAX_TAGS) {
      alert(`Maximum of ${MAX_TAGS} tags allowed`);
      return;
    }

    selectedTags.push(tag);
    createChip(tag);
    updateHiddenInput();
    updateVisibleInput();
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
        tagInput.value = selectedTags.map(t => t.name).join(", ") + ", ";
        suggestionsBox.classList.add("hidden");
      };

      suggestionsBox.appendChild(item);
    });

    suggestionsBox.classList.toggle("hidden", tags.length === 0);
  }

  // ------------------------------
  // Event Listeners
  // ------------------------------
  tagInput.addEventListener("input", () => {
    const value = tagInput.value.split(",").pop().trim();
    if (!value) return (suggestionsBox.classList.add("hidden"));
    fetchTags(value);
  });

  tagInput.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
  
      const parts = tagInput.value.split(",");
      const lastTag = parts[parts.length - 1].trim();
  
      if (!lastTag) return;
  
      addTag({ name: lastTag });
  
      // rebuild input cleanly
      tagInput.value = selectedTags.map(t => t.name).join(", ") + ", ";
      suggestionsBox.classList.add("hidden");
    }
  });

  // Preload existing tags
  if (window.existingTags && Array.isArray(window.existingTags)) {
    window.existingTags.forEach(name => addTag({ name }));
  }

  // Sync hidden input before submit
  form.addEventListener("submit", () => updateHiddenInput());
});