import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0c0d0f",        // charcoal page
        panel: "#141519",
        panel2: "#1a1c21",
        border: "#25272d",
        muted: "#878d98",
        txt: "#e9ebee",
        accent: "#ef7518",    // orange
        accent2: "#ff9a4d",
        bull: "#36c76f",      // success / long
        bear: "#ef5350",      // loss / short
        warn: "#f0a826",      // amber warning
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
