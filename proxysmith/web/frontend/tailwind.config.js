/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        surface: {
          0: '#0c0c0d',
          1: '#0f0f0e',
          2: '#141413',
          3: '#1a1917',
          4: '#1e1d1b',
          5: '#242220',
        },
        ink: {
          1: '#e2e0da',
          2: '#b0ada7',
          3: '#7a7875',
          4: '#4a4845',
          5: '#2e2c28',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.15s ease',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: 0, transform: 'translateY(2px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
