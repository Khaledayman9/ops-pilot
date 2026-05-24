import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        void: "#07070c",
        obsidian: "#0a0a0f",
        plasma: "#00ff88",
        "plasma-dim": "#00cc6a",
        ember: "#ff4444",
        amber: "#ffaa00",
        ice: "#00ccff",
        chrome: "#e0e0e0",
        "chrome-dim": "#888888",
        "surface-1": "#111118",
        "surface-2": "#16161f",
        "surface-3": "#1e1e2a",
        "border-1": "#2a2a3a",
        "border-2": "#3a3a50",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "monospace"],
        display: ["'Space Grotesk'", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;