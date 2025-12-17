/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Kurral brand colors (user-provided palette)
        kurral: {
          navy: '#081A4B',        // Deep navy
          blue: '#0B4DB8',        // Primary blue
          cyan: '#0FA2F2',        // Bright cyan
          'cyan-light': '#4FD6FF', // Light cyan
          purple: '#3A0CA3',      // Deep purple
          'purple-bright': '#6A00F4', // Bright purple
          'purple-mid': '#8E2DE2',    // Mid purple
          'purple-light': '#C63EFF',  // Light purple
          pink: '#F3A6C8',        // Accent pink
        },
        // Agent Prism theme colors (for compatibility)
        'trace': {
          'llm': '#0FA2F2',
          'tool': '#6A00F4',
          'agent': '#0B4DB8',
          'chain': '#8E2DE2',
          'retriever': '#C63EFF',
        },
      },
    },
  },
  plugins: [],
}
