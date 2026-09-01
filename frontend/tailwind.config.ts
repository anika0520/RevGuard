import type { Config } from "tailwindcss";

const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: token("canvas"),
        surface: token("surface"),
        elevated: token("elevated"),
        line: token("line"),
        fg: token("fg"),
        muted: token("muted"),
        subtle: token("subtle"),
        accent: token("accent"),
        "accent-soft": token("accent-soft"),
        success: token("success"),
        warning: token("warning"),
        danger: token("danger"),
        caution: token("caution"),
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(var(--shadow) / 0.06), 0 1px 3px 0 rgb(var(--shadow) / 0.04)",
        raised: "0 4px 12px -2px rgb(var(--shadow) / 0.10), 0 2px 4px -2px rgb(var(--shadow) / 0.06)",
        pop: "0 16px 40px -12px rgb(var(--shadow) / 0.28)",
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};
export default config;
