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
        })
      });
    
      let data = null;
    
      try {
        data = await res.json();
      } catch (jsonErr) {
        throw new Error("Invalid server response");
      }
    
      // Handle ALL error responses first
      if (!res.ok) {
        if (data?.error === "tokens_exhausted") {
          showError(data.message);
          setTimeout(() => { window.location.href = "/pricing"; }, 2500);
          return;
        }
    
        if (data?.error === "premium_required") {
          window.location.href = data.redirect;
          return;
        }
    
        showError(data?.message || "Something went wrong.");
        return;
      }
    
      // Successful response
      renderResults(data);
    
    } catch (err) {
      console.error("Fetch error:", err);
      showError("Server connection issue. Please try again.");
    } finally {
      toggleLoading(false);
    }
  });

  // =========================
  // RENDER RESULTS
  // =========================
  function renderResults(data) {

    if (!data?.captions?.length) return;

    const isPremium = data.type === "premium";

    // BEST CAPTION DIV
    data.captions.forEach((cap) => {
      const capDiv = document.createElement("div");
      capDiv.className = "mb-6 p-4 border-2 border-yellow-400 dark:bg-gray-800 bg-yellow-50 rounded-xl shadow-md";
  
      capDiv.innerHTML = `
        <div class="border-2 border-yellow-400 bg-yellow-50 p-4 rounded-xl mb-2">
          <span class="text-xs font-bold text-yellow-600">CAPTION GENERATED</span>
        </div>
  
        ${isPremium ? `
        <div class="w-full bg-gray-200 rounded-full h-2 mb-6">
          <div class="bg-green-500 h-2 rounded-full" style="width:${cap.confidence_score || 0}%"></div>
        </div>
        ` : ""}
  
        <p class="text-lg text-center font-semibold text-gray-900 dark:text-white">${cap.text}</p>
        <p class="text-gray-500 text-sm mt-1">Style: ${cap.style}</p>
      `;
  
      // COPY BUTTON
      const copyBtn = document.createElement("button");
      copyBtn.className = "px-3 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700 mt-2";
      copyBtn.innerText = "Copy";
      copyBtn.addEventListener("click", () => navigator.clipboard.writeText(cap.text));
      capDiv.appendChild(copyBtn);
  
      results.appendChild(capDiv);
    });

    // THREAD
    if (data.thread?.length) {
      const threadSec = createSection("Thread");
      data.thread.forEach((tweet) => {
        const tweetEl = document.createElement("div");
        tweetEl.className = "p-3 bg-gray-900 rounded text-white cursor-pointer hover:bg-gray-700";
        tweetEl.innerText = tweet.text || tweet;
        tweetEl.addEventListener("click", () => navigator.clipboard.writeText(tweet.text || tweet));
        threadSec.appendChild(tweetEl);
      });
      results.appendChild(threadSec);
    }

    // REPLIES
    if (data.replies?.length) {
      const repliesSec = createSection("Suggested Replies");
      data.replies.forEach((reply) => {
        const el = document.createElement("div");
        el.className = "text-white bg-gray-900 p-2 rounded cursor-pointer hover:bg-gray-700";
        el.innerText = reply;
        el.addEventListener("click", () => navigator.clipboard.writeText(reply));
        repliesSec.appendChild(el);
      });
      results.appendChild(repliesSec);
    }

    // ENGAGEMENT SCORE
    if (data.engagement_score !== undefined && data.engagement_score !== null) {
      const scoreDiv = document.createElement("div");
      scoreDiv.className = "text-center text-green-400 font-bold text-lg mt-4";
      scoreDiv.textContent = `Overall Engagement Score: ${data.engagement_score}`;
      results.appendChild(scoreDiv);
    }

    // TOKENS REMAINING
    if (data.tokens_remaining !== undefined) {
      const tokenDiv = document.getElementById("tokenCount");
      if (tokenDiv) tokenDiv.innerText = `🎟️ Tokens: ${data.tokens_remaining}`;
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
    console.log('Showing error:', msg);
    errorEl.innerText = msg || "An unknown error occurred.";
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