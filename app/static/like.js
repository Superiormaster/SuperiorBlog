/*document.addEventListener("DOMContentLoaded", () => {
  // Like button click
  document.querySelectorAll(".like-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const postId = btn.dataset.postId;
      try {
        const res = await fetch(`/post/${postId}/like`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();

        if (data.liked) {
          btn.querySelector(".like-count").textContent = data.count;
          btn.querySelector("i").classList.replace("far", "fas"); // make thumbs-up solid
        } else {
          btn.querySelector(".like-count").textContent = data.count;
          btn.querySelector("i").classList.replace("fas", "far"); // make thumbs-up outline
        }
      } catch (err) {
        console.error("Error liking post:", err);
      }
    });
  });
});

async function likePost(btn) {
  const postId = btn.dataset.postId;

  try {
    const res = await fetch(`/post/${postId}/like`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin"  // important if login is required
    });

    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      console.error("Response was not valid JSON:", text);
      return;
    }

    btn.querySelector(".like-count").textContent = data.count;
    const icon = btn.querySelector("i");
    icon.classList.toggle("fas", data.liked);
    icon.classList.toggle("far", !data.liked);

  } catch (err) {
    console.error("Like failed:", err);
  }
}