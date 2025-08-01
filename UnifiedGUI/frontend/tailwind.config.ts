import type { Config } from 'tailwindcss';

const config: Config = {
    darkMode: ['class'],
    content: [
    './src/**/*.{ts,tsx}',
  ],
  theme: {
  	extend: {
  		colors: {
  			background: 'hsl(var(--background))',
  			'surface-dark': '#151518',
  			'surface-medium': '#1a1a1f',
  			'surface-light': '#202028',
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			'accent-bright': '#FFB84D',
  			'accent-dim': '#CC8100',
  			warning: '#FF6B35',
  			success: '#00D9FF',
  			danger: '#FF4757',
  			'text-primary': '#FFFFFF',
  			'text-secondary': '#B8BCC8',
  			'text-tertiary': '#6C7293',
  			'border-primary': '#333342',
  			'border-glow': '#FFA200',
  			// Beachside palette
  			'beachside-dark': '#3B7097',
  			'beachside-medium': '#75BDE0', 
  			'beachside-light': '#A9D09E',
  			'beachside-sand': '#F6E2BC',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		boxShadow: {
  			glow: '0 0 10px rgba(255, 162, 0, 0.3)',
  			'glow-strong': '0 0 20px rgba(255, 162, 0, 0.5)',
  			'inner-glow': 'inset 0 0 10px rgba(255, 162, 0, 0.2)',
  			tactical: '0 4px 20px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 162, 0, 0.2)'
  		},
  		fontFamily: {
  			mono: [
  				'SF Mono',
  				'Monaco',
  				'Consolas',
  				'monospace'
  			],
  			tactical: [
  				'Inter',
  				'system-ui',
  				'sans-serif'
  			]
  		},
  		animation: {
  			'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
  			'scan-line': 'scan-line 3s linear infinite',
  			'data-flow': 'data-flow 4s ease-in-out infinite',
  			'spin-slow': 'spin 20s linear infinite'
  		},
  		keyframes: {
  			'pulse-glow': {
  				'0%, 100%': {
  					boxShadow: '0 0 5px rgba(255, 162, 0, 0.3)'
  				},
  				'50%': {
  					boxShadow: '0 0 20px rgba(255, 162, 0, 0.8)'
  				}
  			},
  			'scan-line': {
  				'0%': {
  					transform: 'translateY(-100%)'
  				},
  				'100%': {
  					transform: 'translateY(100vh)'
  				}
  			},
  			'data-flow': {
  				'0%, 100%': {
  					opacity: '0.5'
  				},
  				'50%': {
  					opacity: '1'
  				}
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};

export default config; 