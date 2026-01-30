// caption.js
document.addEventListener("DOMContentLoaded", () => {
  const textInput = document.getElementById("text");
  const charCount = document.getElementById("charCount");
  const results = document.getElementById("results");
  const generateBtn = document.getElementById("generateBtn");

  // Character counter
  if (textInput) {
    textInput.addEventListener("input", () => {
      charCount.innerText = `Characters: ${textInput.value.length}`;
    });
  }

  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      const text = textInput.value.trim();
      if (!text) {
        results.innerHTML = `<p class="text-red-500">Please enter some text to generate captions.</p>`;
        return;
      }
  
      // Button loading state
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
        if (!res.ok) {
          results.innerHTML = `<p class="text-red-500">${data.error || 'Something went wrong.'}</p>`;
          return;
        }
  
        results.innerHTML = "";
  
        if (!data.results || !data.results.length) {
          results.innerHTML = `<p class="text-gray-400">No captions generated.</p>`;
          return;
        }
  
        if (data.error) {
          results.innerHTML = `<p class="text-red-500">${data.error}</p>`;
          return;
        }
  
        data.results.forEach(item => {
          const card = document.createElement("div");
          card.className =
            "bg-gray-800 p-4 rounded-xl shadow-md space-y-3 border border-gray-700";
  
          const header = document.createElement('div');
          header.className = "flex justify-between items-center";
          header.innerHTML = `
            <h3 class="font-semibold text-lg">${item.style === "safe" ? "📰 Safe" :
                                               item.style === "viral" ? "🔥 Viral" :
                                               "🧠 Editor Pick"}</h3>
            <span class="text-sm text-gray-400">Confidence: ${item.confidence}%</span>
          `;
          card.appendChild(header);
  
          // Caption text
          const captionText = document.createElement('p');
          captionText.className = 'text-white text-md leading-relaxed';
          captionText.innerText = item.caption;
          card.appendChild(captionText);
  
          // Optional reason
          if (item.reason) {
            const reasonEl = document.createElement('p');
            reasonEl.className = 'text-gray-400 italic text-sm';
            reasonEl.innerText = `Why this works: ${item.reason}`;
            card.appendChild(reasonEl);
          }
  
          const copyBtn = document.createElement('button');
          copyBtn.className = 'px-4 py-2 text-xs rounded-lg bg-blue-600 hover:bg-blue-700';
          copyBtn.innerText = 'Copy';
          copyBtn.addEventListener('click', () => navigator.clipboard.writeText(item.caption));
          card.appendChild(copyBtn);
  
          results.appendChild(card);
        });
      } catch (err) {
        console.error(err);
        results.innerHTML = `<p class="text-red-500">${
          err.error || "Something went wrong. Please try again."
        }</p>`;
      } finally {
        generateBtn.disabled = false;
        generateBtn.innerText = "Generate";
      }
    });
  }
});