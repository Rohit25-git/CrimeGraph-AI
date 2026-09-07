/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#f8fafc",
        card: "#ffffff",
        border: "#e2e8f0",
        primary: "#0f172a",
        accent: "#2563eb",
        rgb: {
          red: "rgb(239, 68, 68)",
          green: "rgb(16, 185, 129)",
          blue: "rgb(59, 130, 246)",
          amber: "rgb(245, 158, 11)",
          purple: "rgb(168, 85, 247)",
          cyan: "rgb(6, 182, 212)",
          rose: "rgb(244, 63, 94)",
        },
        alert: {
          high: "#dc2626",
          medium: "#d97706",
          low: "#16a34a",
          info: "#2563eb"
        }
      }
    },
  },
  plugins: [],
}
