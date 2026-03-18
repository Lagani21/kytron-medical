/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      colors: {
        kyron: {
          bg:       '#080B1A',
          surface:  '#0D1129',
          elevated: '#111530',
          blue:     '#2563EB',
          'blue-hover': '#1D4ED8',
          'blue-text':  '#60A5FA',
          purple:   '#7C3AED',
          success:  '#10B981',
          warning:  '#F59E0B',
          danger:   '#EF4444',
          purple2:  '#A78BFA',
        },
      },
    },
  },
  plugins: [],
}
