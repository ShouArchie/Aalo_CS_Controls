import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#101012',
        accent: '#FFA200',
      },
      boxShadow: {
        glow: '0 0 6px #FFA200',
      },
    },
  },
  plugins: [],
};

export default config; 