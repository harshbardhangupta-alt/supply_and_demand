import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0e14",
        panel: "#111722",
        panel2: "#0d131c",
        border: "#1e2735",
        muted: "#8a97a8",
        txt: "#e6edf3",
        accent: "#4f8cff",
        bull: "#26a69a",
        bear: "#ef5350",
        warn: "#f0b429",
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
