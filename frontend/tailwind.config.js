/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'mixer': {
          'bg': '#1a1a2e',
          'panel': '#252541',
          'fader': '#16213e',
          'meter-green': '#00ff00',
          'meter-yellow': '#ffff00',
          'meter-red': '#ff0000',
          'channel-red': '#e74c3c',
          'channel-green': '#2ecc71',
          'channel-blue': '#3498db',
          'channel-yellow': '#f1c40f',
          'channel-magenta': '#9b59b6',
          'channel-cyan': '#1abc9c',
        }
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
