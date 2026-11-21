/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        finwell: {
          bg: '#080914',
          sidebar: '#0D0E1B',
          card: '#121426',
          surface: '#191C30',
          hover: '#1E223D',
          border: 'rgba(255, 255, 255, 0.08)',
          borderGlow: 'rgba(66, 99, 255, 0.3)',
          primary: '#4263FF',
          'primary-hover': '#3250EC',
          cyan: '#20D9F2',
          violet: '#875BFF',
          text: '#F5F6FF',
          muted: '#9298B3',
          dim: '#656B8A',
          success: '#36D399',
          warning: '#FBBF24',
          danger: '#FB7185',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-sm': '0 0 15px rgba(66, 99, 255, 0.2)',
        'glow-md': '0 0 30px rgba(66, 99, 255, 0.25)',
        'glow-lg': '0 0 50px rgba(66, 99, 255, 0.35)',
        'glow-cyan': '0 0 30px rgba(32, 217, 242, 0.25)',
        'glow-violet': '0 0 30px rgba(135, 91, 255, 0.25)',
        'card-glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        glowPulse: {
          '0%': { opacity: '0.4', filter: 'blur(20px)' },
          '100%': { opacity: '0.8', filter: 'blur(30px)' },
        }
      }
    },
  },
  plugins: [],
}
