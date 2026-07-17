/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        jukebox: {
          deep: '#0f172a',
          surface: '#1e293b',
          accent: '#a855f7',
          primary: '#f8fafc',
          muted: '#94a3b8'
        }
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
};
