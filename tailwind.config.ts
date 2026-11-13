import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { bg: "var(--bg)", card: "var(--card)", ink: "var(--ink)", mute: "var(--mute)", brand: "#705CF6", graphite: "#17181C",
              ok: "#20B982", bad: "#E65A65", line: "var(--line)" },
    borderRadius: { card: "20px", xl2: "24px" },
    fontFamily: { sans: ["Inter", "-apple-system", "SF Pro Display", "Segoe UI", "Roboto", "sans-serif"] },
  } },
  plugins: [],
} satisfies Config;
