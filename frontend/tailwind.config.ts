import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        void: "var(--void)",
        obsidian: "var(--obsidian)",
        plasma: "var(--plasma)",
        "plasma-dim": "var(--plasma-dim)",
        ember: "var(--ember)",
        amber: "var(--amber)",
        ice: "var(--ice)",
        chrome: "var(--chrome)",
        "chrome-dim": "var(--chrome-dim)",
        "surface-1": "var(--surface-1)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        "border-1": "var(--border-1)",
        "border-2": "var(--border-2)",
      },
      fontFamily: {
        mono: ["var(--font-jetbrains-mono)", "JetBrains Mono", "monospace"],
        display: ["var(--font-space-grotesk)", "Space Grotesk", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
