import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./stores/**/*.{ts,tsx}",
    "./services/**/*.{ts,tsx}",
  ],
  theme: { extend: {} },
  plugins: [typography],
};

export default config;
