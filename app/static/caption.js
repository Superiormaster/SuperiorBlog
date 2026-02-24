document.addEventListener("DOMContentLoaded", () => {

  const form = document.getElementById("xGeneratorForm");
  if (!form) return;

  const textInput = document.getElementById("xText");
  const results = document.getElementById("xResults");
  const loading = document.getElementById("xLoading");
  const errorEl = document.getElementById("xError");
  const generateBtn = document.getElementById("xGenerateBtn");
  const charCount = document.getElementById("charCount");

  // =========================
  // CHARACTER COUNTER
  // =========================
  if (textInput && charCount) {
    const updateCount = () => {
      const length = textInput.value.length;
      charCount.textContent = `${length} / 500`;

      charCount.classList.toggle("text-red-500", length > 500);
      charCount.classList.toggle("text-gray-400", length <= 500);
      generateBtn.disabled = length === 0 || length > 500;
    };

    textInput.addEventListener("input", updateCount);
    updateCount();
  }

  // =========================
  // FORM SUBMISSION
  // =========================
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const text = textInput.value.trim();
    if (!text) return showError("Please enter some text.");

    toggleLoading(true);
    results.innerHTML = "";

    try {
      const res = await fetch("/caption/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          text,
          tone: document.getElementById("xTone").value,
          mode: document.getElementById("xMode").value,
          avoid_clickbait: document.getElementById("xAvoidClickbait").checked,
          generate_image: document.getElementById("xGenerateImage").checked
        })
      });

      if (!res.ok) throw new Error("Server error");

      const data = await res.json();

      if (data.error) {
        if (data.error === "premium_required") {
          window.location.href = data.redirect;
          return;
        }
        return showError(data.error);
      }

      renderResults(data);

    } catch (err) {
      console.error(err);
      showError("Something went wrong. Try again.");
    } finally {
      toggleLoading(false);
    }
  });

  // =========================
  // RENDER RESULTS
  // =========================
  function renderResults(data) {

    if (!data?.captions?.length) return;

    // BEST CAPTION (FIRST)
    const best = data.captions[0];

    const bestDiv = document.createElement("div");
    bestDiv.className = "mb-6 p-4 border-2 border-yellow-400 bg-yellow-50 rounded-xl shadow-md";

    bestDiv.innerHTML = `
      <div class="border-2 border-yellow-400 bg-yellow-50 p-4 rounded-xl mb-2">
        <span class="text-xs font-bold text-yellow-600">BEST CAPTION</span>
      </div>

      <div class="w-full bg-gray-200 rounded-full h-2 mb-6">
        <div class="bg-green-500 h-2 rounded-full"
             style="width:${best.confidence_score || 80}%"></div>
      </div>

      <p class="text-lg text-center font-semibold text-gray-900 dark:text-white">
        ${best.text}
      </p>

      ${best.image_url ? `
        <div class="relative w-full h-64 bg-gray-700 rounded-xl overflow-hidden mt-2">
          <img src="${Array.isArray(best.image_url) ? best.image_url[0] : best.image_url}"
               class="absolute inset-0 w-full h-full object-cover rounded-xl">
        </div>
      ` : ""}

      <p class="text-gray-500 text-sm mt-1">
        Style: ${best.style}, Confidence: ${best.confidence_score}%
      </p>

      <p class="text-gray-500 text-sm mt-1">
        Suggested Replies: ${best.suggested_replies ? best.suggested_replies.join(", ") : ""}
      </p>

      <p class="text-gray-500 text-sm mt-1">
        Best Posting Time: ${best.best_post_time}
      </p>
    `;

    results.appendChild(bestDiv);

    // OTHER CAPTIONS
    data.captions.slice(1).forEach(cap => {
      const card = document.createElement("div");
      card.className = "bg-gray-800 p-4 rounded-xl shadow-md space-y-2";

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

      const copyBtn = document.createElement("button");
      copyBtn.className = "px-3 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700";
      copyBtn.innerText = "Copy";
      copyBtn.addEventListener("click", () =>
        navigator.clipboard.writeText(cap.text)
      );

      card.appendChild(copyBtn);
      results.appendChild(card);
    });

    // THREAD
    if (data.thread?.length) {
      const threadSec = createSection("Thread");

      data.thread.forEach((tweet, i) => {
        const tweetEl = document.createElement("div");
        tweetEl.className = "p-3 bg-gray-900 rounded text-white cursor-pointer hover:bg-gray-700";
        tweetEl.innerText = tweet.text || tweet;

        tweetEl.addEventListener("click", () =>
          navigator.clipboard.writeText(tweet.text || tweet)
        );

        threadSec.appendChild(tweetEl);
      });

      results.appendChild(threadSec);
    }

    // REPLIES
    if (data.replies?.length) {
      const repliesSec = createSection("Suggested Replies");

      data.replies.forEach(reply => {
        const el = document.createElement("div");
        el.className = "text-white bg-gray-900 p-2 rounded cursor-pointer hover:bg-gray-700";
        el.innerText = reply;
        el.addEventListener("click", () =>
          navigator.clipboard.writeText(reply)
        );
        repliesSec.appendChild(el);
      });

      results.appendChild(repliesSec);
    }

    // ENGAGEMENT SCORE
    if (data.engagement_score) {
      const scoreDiv = document.createElement("div");
      scoreDiv.className = "text-center text-green-400 font-bold text-lg mt-4";
      scoreDiv.textContent = `Overall Engagement Score: ${data.engagement_score}`;
      results.appendChild(scoreDiv);
    }
  }

  // =========================
  // HELPERS
  // =========================
  function toggleLoading(show) {
    loading?.classList.toggle("hidden", !show);
    generateBtn.disabled = show;
    generateBtn.innerText = show ? "Generating..." : "Generate X Content";
  }

  function showError(msg) {
    errorEl.innerText = msg;
    errorEl.classList.remove("hidden");
    setTimeout(() => errorEl.classList.add("hidden"), 5000);
  }

  function createSection(title) {
    const sec = document.createElement("div");
    sec.className = "space-y-4 mt-6";

    const header = document.createElement("h3");
    header.className = "text-lg font-bold text-white mb-2";
    header.innerText = title;

    sec.appendChild(header);
    return sec;
  }

});