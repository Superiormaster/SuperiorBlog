/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./app/templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        lightBg: '#ffffff',
        lightText: '#1f2937',   // gray-800
        darkBg: '#111827',       // gray-900
        darkText: '#f3f4f6',     // gray-100
        headerBgLight: '#f9fafb', 
        headerBgDark: '#1f2937',
      },
    },
  },
  plugins: [],
}

