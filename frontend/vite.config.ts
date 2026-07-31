/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    // jsdom, not 'node': story 1.6 adds component tests that need `document`
    // and `window` (React Testing Library). index.css.test.ts's plain
    // node:fs reads still work fine under jsdom -- it only adds browser
    // globals, it does not remove Node's own APIs.
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
})
