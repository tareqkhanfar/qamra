/** Qamra (قمرة) — Tailwind config generated from tokens.json */
/** Use with <html lang="ar" dir="rtl">. Dark mode via class="dark" on <html>. */
module.exports = {
  content: ['./src/**/*.{html,js,jsx,ts,tsx,vue}', './design/**/*.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        night: { 950: '#0E1530', 900: '#16204A', 800: '#22306A', 700: '#33458F', 500: '#5B6FC0', 100: '#E4E8F7' },
        amber: { 700: '#9A620A', 600: '#DB9A1F', 500: '#F2B33D', 300: '#F5C465', 100: '#FCEFD2' },
        moon: { DEFAULT: '#F2B33D', glow: '#FCEFD2', night: '#22306A', deep: '#9A620A' },
        paper: { DEFAULT: '#FBF6EC', raised: '#FFFDF8', sunk: '#F3EAD8' },
        line: { DEFAULT: '#E4D6BC', dark: '#2B3872' },
        ink: { DEFAULT: '#1C2140', muted: '#585C72', faint: '#8A8DA0', dark: '#F6EFDF', 'dark-muted': '#B9BEDA' },
        sage: { 700: '#3E6B4D', 300: '#A9C7B1' },
        coral: { 700: '#A7432D', 300: '#F4B3A2' },
        lav: { 700: '#5A4A9C', 300: '#CBC1EA' },
        success: { DEFAULT: '#2E7A52', bg: '#DDEFE3' },
        danger: { DEFAULT: '#B3261E', bg: '#F8DEDB' },
        warning: { DEFAULT: '#9A620A', bg: '#FCEFD2' },
        info: { DEFAULT: '#33458F', bg: '#E4E8F7' },
      },
      fontFamily: {
        display: ['"Baloo Bhaijaan 2"', 'Tajawal', 'system-ui', 'sans-serif'],
        body: ['"IBM Plex Sans Arabic"', '"Segoe UI"', 'Tahoma', 'sans-serif'],
      },
      fontSize: {
        'display-xl': ['64px', { lineHeight: '1.15', fontWeight: '800' }],
        'display-l': ['48px', { lineHeight: '1.2', fontWeight: '800' }],
        h1: ['36px', { lineHeight: '1.25', fontWeight: '700' }],
        h2: ['28px', { lineHeight: '1.3', fontWeight: '700' }],
        h3: ['22px', { lineHeight: '1.35', fontWeight: '700' }],
        'body-l': ['18px', { lineHeight: '1.75' }],
        body: ['16px', { lineHeight: '1.7' }],
        small: ['14px', { lineHeight: '1.6' }],
        caption: ['13px', { lineHeight: '1.5', fontWeight: '600' }],
      },
      borderRadius: { sm: '12px', md: '16px', lg: '20px', xl: '24px', '2xl': '28px', book: '16px 4px 4px 16px' },
      boxShadow: {
        1: '0 1px 2px rgba(22,32,74,0.06), 0 2px 8px rgba(22,32,74,0.06)',
        2: '0 8px 24px rgba(22,32,74,0.12)',
        book: '0 16px 40px rgba(22,32,74,0.18)',
        lamp: '0 8px 28px rgba(242,179,61,0.45)',
      },
      minHeight: { tap: '44px', btn: '56px', input: '52px' },
      minWidth: { tap: '44px' },
      backgroundImage: {
        paper: 'radial-gradient(rgba(28,33,64,0.035) 1px, transparent 1px)',
      },
      backgroundSize: { paper: '7px 7px' },
      keyframes: {
        twinkle: { '0%,100%': { opacity: '1', transform: 'scale(1)' }, '50%': { opacity: '.35', transform: 'scale(.8)' } },
        float: { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-10px)' } },
      },
      animation: { twinkle: 'twinkle 2.4s ease-in-out infinite', float: 'float 3.2s ease-in-out infinite' },
    },
  },
  plugins: [],
};

/*
 Font setup — put in <head>:
 <link rel="preconnect" href="https://fonts.googleapis.com">
 <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
 <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Baloo+Bhaijaan+2:wght@500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap">

 Base layer (src/styles.css):
 @tailwind base; @tailwind components; @tailwind utilities;
 @layer base {
   html { @apply bg-paper text-ink font-body; }
   html.dark { @apply bg-night-950 text-ink-dark; }
   h1,h2,h3,h4 { @apply font-display; text-wrap: balance; }
   :focus-visible { outline: 3px solid #F2B33D; outline-offset: 2px; }
 }
 Use logical utilities (ms-*, me-*, ps-*, pe-*, start-*, end-*) — never ml/mr — so RTL mirrors correctly.
 Directional icons (arrows, chevrons, stepper): add `rtl:-scale-x-100` when the source SVG points right.
*/
