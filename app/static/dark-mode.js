const toggleBtn = document.getElementById("darkModeToggle");
toggleBtn.addEventListener("click", () => {
  document.documentElement.classList.toggle("dark");
  localStorage.setItem("darkMode", document.documentElement.classList.contains("dark"));
});

// Load preference on page load
if (localStorage.getItem("darkMode") === "true") {
  document.documentElement.classList.add("dark");
}