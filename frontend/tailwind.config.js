/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        xhs: {
          red: '#ff2442',
          gray: '#f5f5f5',
          dark: '#333333'
        }
      }
    },
  },
  plugins: [],
}
