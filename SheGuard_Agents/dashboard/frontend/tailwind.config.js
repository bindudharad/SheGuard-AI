/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#0a0e17',
          secondary: '#0f1422',
          card: '#131a2b',
          elevated: '#1a2336',
        },
        accent: {
          DEFAULT: '#38bdf8',
          glow: '#0ea5e9',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px rgba(56, 189, 248, 0.15)',
        'glow-lg': '0 0 40px rgba(56, 189, 248, 0.25)',
      },
    },
  },
  plugins: [],
}
