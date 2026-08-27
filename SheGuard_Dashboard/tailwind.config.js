/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        command: {
          DEFAULT: '#07090f',
          950: '#07090f',
          900: '#0c1018',
          800: '#121826',
          700: '#1b2435',
        },
        alert: {
          500: '#ff2e3f',
          600: '#e1112a',
          700: '#b90b1f',
        },
      },
      boxShadow: {
        glow: '0 0 30px rgba(255, 46, 63, 0.32)',
        panel: '0 20px 80px rgba(0, 0, 0, 0.42)',
      },
      animation: {
        'sos-pulse': 'sosPulse 1.35s ease-in-out infinite',
        scan: 'scan 4s linear infinite',
        float: 'float 6s ease-in-out infinite',
      },
      keyframes: {
        sosPulse: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.08)', opacity: '0.68' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
      },
    },
  },
  plugins: [],
};
