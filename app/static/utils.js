// utils.js

export function setSafeRedirect(url) {
  try {
    if (!url) throw new Error("Invalid redirect");
    window.location.assign(url);
  } catch {
    window.location.assign("/");
  }
}