import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#3b82f6', dark: '#2563eb', light: '#93c5fd' },
        secondary: { DEFAULT: '#8b5cf6', dark: '#7c3aed' },
        surface: '#1e293b',
        'surface-alt': '#0f172a',
      },
    },
  },
  plugins: [],
}

export default config
