// caption.js
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.add('hidden'));
    document.getElementById(`tab-${tab}`).classList.remove('hidden');
  });
});

item.addEventListener('click', () => {
  captions.classList.toggle('show');
});

<script>
document.addEventListener("DOMContentLoaded", () => {
  const textInput = document.getElementById("text");
  const charCount = document.getElementById("charCount");
  const results = document.getElementById("results");
  const generateBtn = document.getElementById("generateBtn");

  if (textInput) {
    textInput.addEventListener("input", () => {
      charCount.innerText = `Characters: ${textInput.value.length}`;
    });
  }

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const tab = btn.dataset.tab;
      document.querySelectorAll('.result-section').forEach(sec => sec.classList.add('hidden'));
      const target = document.getElementById(`tab-${tab}`);
      if (target) target.classList.remove('hidden');
    });
  });

  // Generate captions
  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      const text = textInput.value.trim();
      if (!text) {
        results.innerHTML = `<p class="text-red-500">Please enter some text to generate captions.</p>`;
        return;
      }

      generateBtn.disabled = true;
      generateBtn.innerText = "Generating...";
      results.innerHTML = `<p class="text-gray-400">⏳ Generating captions…</p>`;

      try {
        const res = await fetch("/caption/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            text,
            tone: document.getElementById("tone").value,
            platform: document.getElementById("platform").value,
            length: document.getElementById("length").value
          })
        });

        const data = await res.json();
        results.innerHTML = "";

        if (!data.results || !data.results.length) {
          results.innerHTML = `<p class="text-gray-400">No captions generated.</p>`;
          return;
        }

        // Separate sections for tabs
        const freeSec = document.createElement("div");
        freeSec.id = "tab-free";
        freeSec.className = "result-section";
        const premiumSec = document.createElement("div");
        premiumSec.id = "tab-premium";
        premiumSec.className = "result-section hidden";
        const threadSec = document.createElement("div");
        threadSec.id = "tab-thread";
        threadSec.className = "result-section hidden";

        data.results.forEach(item => {
          const card = document.createElement("div");
          card.className = "bg-gray-800 p-4 rounded-xl shadow-md space-y-2 border border-gray-700";

          const header = document.createElement("div");
          header.className = "flex justify-between items-center";
          header.innerHTML = `<h3 class="font-semibold text-lg">${item.style}</h3>
                              <span class="text-sm text-gray-400">Confidence: ${item.confidence_score}%</span>`;
          card.appendChild(header);

          const captionText = document.createElement("p");
          captionText.className = "text-white";
          captionText.innerText = item.caption;
          card.appendChild(captionText);

          const copyBtn = document.createElement("button");
          copyBtn.className = "px-3 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700 mt-2";
          copyBtn.innerText = "Copy Caption";
          copyBtn.addEventListener("click", () => navigator.clipboard.writeText(item.caption));
          card.appendChild(copyBtn);

          if (item.type === "free") freeSec.appendChild(card);
          else premiumSec.appendChild(card);
        });

        // Thread
        if (data.thread && data.thread.tweets) {
          data.thread.tweets.forEach(t => {
            const tweetEl = document.createElement("p");
            tweetEl.className = "text-white mb-1 p-1 bg-gray-900 rounded cursor-pointer";
            tweetEl.innerText = t;
            tweetEl.addEventListener("click", () => navigator.clipboard.writeText(t));
            threadSec.appendChild(tweetEl);
          });
        }

        results.appendChild(freeSec);
        results.appendChild(premiumSec);
        results.appendChild(threadSec);

      } catch (err) {
        console.error(err);
        results.innerHTML = `<p class="text-red-500">Something went wrong. Please try again.</p>`;
      } finally {
        generateBtn.disabled = false;
        generateBtn.innerText = "Generate X Content";
      }
    });
  }
});
</script>
