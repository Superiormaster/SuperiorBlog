document.addEventListener("DOMContentLoaded", () => {

  const textInput   = document.getElementById("text");
  const charCount   = document.getElementById("charCount");
  const results     = document.getElementById("results");
  const generateBtn = document.getElementById("generateBtn");

  // =========================
  // Character Counter
  // =========================
  if (textInput) {
    textInput.addEventListener("input", () => {
      charCount.innerText = `Characters: ${textInput.value.length}`;
    });
  }

  // =========================
  // Tabs
  // =========================
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const tab = btn.dataset.tab;
      document.querySelectorAll(".result-section")
        .forEach(sec => sec.classList.add("hidden"));

      const target = document.getElementById(`tab-${tab}`);
      if (target) target.classList.remove("hidden");
    });
  });

  // =========================
  // Generate
  // =========================
  if (!generateBtn) return;

  generateBtn.addEventListener("click", async () => {

    const text = textInput.value.trim();

    if (!text) {
      results.innerHTML = `<p class="text-red-500">Please enter some text.</p>`;
      return;
    }

    generateBtn.disabled = true;
    generateBtn.innerText = "Generating...";
    results.innerHTML = `<p class="text-gray-400">⏳ Generating content...</p>`;

    try {

      const res = await fetch("/caption/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          text,
          tone: document.getElementById("tone").value,
          mode: document.getElementById("mode").value,
          avoid_clickbait: document.getElementById("avoid_clickbait").checked,
          length: document.getElementById("length") ? document.getElementById("length").value : "short",
          platform: document.getElementById("platform") ? document.getElementById("platform").value : "x"
        })
      });

      const data = await res.json();
      if (data.error === "premium_required") {
        window.location.href = data.redirect;
        return;
      }

      results.innerHTML = "";

      // =========================
      // Create Sections
      // =========================
      const freeSec    = createSection("tab-free", false);
      const premiumSec = createSection("tab-premium", true);
      const threadSec  = createSection("tab-thread", true);

      // =========================
      // Render Captions
      // =========================
      if (data.captions && data.captions.length) {

        data.captions.forEach(cap => {

          const card = document.createElement("div");
          card.className =
            "bg-gray-800 p-4 rounded-xl shadow-md border border-gray-700 space-y-2";

          card.innerHTML = `
            <div class="flex justify-between items-center">
              <h3 class="font-semibold text-lg capitalize">${cap.style}</h3>
              <span class="text-sm text-gray-400">
                Confidence: ${cap.confidence_score}%
              </span>
            </div>

            <p class="text-white">${cap.text}</p>

            <div class="text-xs text-gray-400">
              Best Time: ${cap.best_post_time}
            </div>
          `;

          // Copy button
          const copyBtn = document.createElement("button");
          copyBtn.className =
            "px-3 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700";
          copyBtn.innerText = "Copy";
          copyBtn.addEventListener("click", () =>
            navigator.clipboard.writeText(cap.text)
          );

          card.appendChild(copyBtn);

          if (data.type === "free") {
            freeSec.appendChild(card);
          } else {
            premiumSec.appendChild(card);
          }

        });
      }

      // =========================
      // Render Thread
      // =========================
      if (data.thread && Array.isArray(data.thread)) {

        data.thread.forEach(tweet => {
          const tweetEl = document.createElement("div");
          tweetEl.className =
            "p-3 bg-gray-900 rounded text-white cursor-pointer hover:bg-gray-700";

          tweetEl.innerText = tweet;

          tweetEl.addEventListener("click", () =>
            navigator.clipboard.writeText(tweet)
          );

          threadSec.appendChild(tweetEl);
        });

      }

      // =========================
      // Append Sections
      // =========================
      results.appendChild(freeSec);
      results.appendChild(premiumSec);
      results.appendChild(threadSec);

    } catch (err) {
      console.error(err);
      results.innerHTML =
        `<p class="text-red-500">Something went wrong. Try again.</p>`;
    }

    generateBtn.disabled = false;
    generateBtn.innerText = "Generate X Content";

  });


  // =========================
  // Helper
  // =========================
  function createSection(id, hidden = false) {
    const sec = document.createElement("div");
    sec.id = id;
    sec.className = "result-section space-y-4";
    if (hidden) sec.classList.add("hidden");
    return sec;
  }

});