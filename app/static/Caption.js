const form = document.getElementById("xGeneratorForm");
const resultsDiv = document.getElementById("xResults");
const loadingDiv = document.getElementById("xLoading");
const errorDiv = document.getElementById("xError");
const generateBtn = document.getElementById("xGenerateBtn");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const text = document.getElementById("xText").value.trim();
  const tone = document.getElementById("xTone").value;
  const mode = document.getElementById("xMode").value;
  const avoid_clickbait = document.getElementById("xAvoidClickbait").checked;
  const generate_images = document.getElementById("xGenerateImage").checked;

  if (!text) {
    errorDiv.textContent = "Please enter content.";
    errorDiv.classList.remove("hidden");
    return;
  }

  errorDiv.classList.add("hidden");
  resultsDiv.innerHTML = "";
  loadingDiv.classList.remove("hidden");
  generateBtn.disabled = true;

  const isCustomPrompt = /Viral Story Creator|Write a powerful|Create a story/i.test(text);

  try {
    const response = await fetch("/api/generate_x_post", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text,
        tone,
        mode,
        avoid_clickbait,
        generate_images,
        custom_prompt: isCustomPrompt ? text : null
      })
    });

    const result = await response.json();

    loadingDiv.classList.add("hidden");
    generateBtn.disabled = false;

    renderResults(result);

  } catch (err) {
    loadingDiv.classList.add("hidden");
    generateBtn.disabled = false;
    errorDiv.textContent = "Something went wrong. Please try again.";
    errorDiv.classList.remove("hidden");
  }
});

function renderResults(result) {
  resultsDiv.innerHTML = "";

  // CAPTIONS
  result.captions.forEach(c => {
    const card = document.createElement("div");
    card.className = "bg-gray-900 p-5 rounded-xl shadow-lg";

    card.innerHTML = `
      <p class="text-white text-lg mb-2">${c.text}</p>
      <p class="text-gray-400 text-sm">
        Style: ${c.style} |
        Confidence: ${c.confidence_score}% |
        Best Time: ${c.best_post_time}
      </p>
      ${c.image_url ? `<img src="${c.image_url}" class="mt-3 rounded-lg w-full object-cover" />` : ""}
    `;

    resultsDiv.appendChild(card);
  });

  // THREAD
  if (result.thread && result.thread.length > 0) {
    const threadDiv = document.createElement("div");
    threadDiv.className = "bg-gray-800 p-5 rounded-xl";

    threadDiv.innerHTML = "<h3 class='text-white font-bold mb-3'>Thread</h3>";

    result.thread.forEach((t, i) => {
      threadDiv.innerHTML += `
        <div class="mb-3">
          <p class="text-white">Tweet ${i+1}: ${t.text}</p>
          ${t.image_url ? `<img src="${t.image_url}" class="mt-2 rounded-lg w-full" />` : ""}
        </div>
      `;
    });

    resultsDiv.appendChild(threadDiv);
  }

  // REPLIES
  if (result.replies && result.replies.length > 0) {
    const repliesDiv = document.createElement("div");
    repliesDiv.className = "bg-gray-800 p-5 rounded-xl";

    repliesDiv.innerHTML = "<h3 class='text-white font-bold mb-3'>Suggested Replies</h3><ul class='list-disc pl-5 text-white'>";

    result.replies.forEach(r => {
      repliesDiv.innerHTML += `<li>${r}</li>`;
    });

    repliesDiv.innerHTML += "</ul>";

    resultsDiv.appendChild(repliesDiv);
  }

  // OVERALL SCORE
  const scoreDiv = document.createElement("div");
  scoreDiv.className = "text-center text-green-400 font-bold text-lg mt-4";
  scoreDiv.innerHTML = `Overall Engagement Score: ${result.engagement_score}`;

  resultsDiv.appendChild(scoreDiv);
}