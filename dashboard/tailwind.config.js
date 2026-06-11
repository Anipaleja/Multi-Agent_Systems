export default {
  content: ['./index.html', './src/**/*.{jsx,js}'],
  theme: {
    fontFamily: {
      serif: ['Cormorant Garamond', 'Georgia', 'serif'],
      sans:  ['Inter', 'system-ui', 'sans-serif'],
      mono:  ['JetBrains Mono', 'Menlo', 'monospace'],
    },
    extend: {
      colors: {
        brand: {
          bg:          '#eef0f7',
          surface:     '#ffffff',
          navy:        '#0d1530',
          'navy-mid':  '#2d3561',
          blue:        '#4f5fc4',
          'blue-dim':  '#eceeff',
          teal:        '#2d8a6e',
          'teal-dim':  '#e4f4ef',
          muted:       '#8b93b8',
          'muted-dim': '#c4c8e2',
          border:      '#e2e4f0',
          'border-mid':'#ccd0e8',
        },
      },
      letterSpacing: {
        widest: '0.2em',
      },
    },
  },
  plugins: [],
}
