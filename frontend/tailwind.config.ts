import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#05070a",        // near-black
        panel: "#0b1016",
        panel2: "#070b0f",
        border: "#17211c",    // dark green-tinted border
        muted: "#79887f",
        txt: "#e9f2ec",
        accent: "#2bff88",    // neon green
        neon: "#2bff88",
        bull: "#2bff88",
        bear: "#ff4d5e",
        warn: "#ffd166",
      },
      boxShadow: {
        neon: "0 0 0 1px rgba(43,255,136,0.25), 0 0 18px rgba(43,255,136,0.12)",
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
