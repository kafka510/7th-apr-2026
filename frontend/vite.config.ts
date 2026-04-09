/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dirname =
  typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

/** Single physical install — prevents duplicate React across chunks (fixes null `useEffect` in prod). */
const reactRoot = path.resolve(dirname, 'node_modules/react');
const reactDomRoot = path.resolve(dirname, 'node_modules/react-dom');

/** Pin React + scheduler into one async chunk so feature code never resolves a second `react` copy. */
function manualChunksReactVendor(id: string): string | undefined {
  const n = id.replace(/\\/g, '/');
  if (n.includes('/node_modules/react-dom/')) return 'react-vendor';
  if (n.includes('/node_modules/scheduler/')) return 'react-vendor';
  if (/\/node_modules\/react\//.test(n)) return 'react-vendor';
  return undefined;
}

// Storybook test configuration is commented out to avoid build errors
// Uncomment and install Storybook dependencies if you need to run Storybook tests
// import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
// import { playwright } from '@vitest/browser-playwright';

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig(({ command }) => ({
  /**
   * Production chunks must load under Django static URL prefix. Default Vite base `/` makes
   * dynamic imports request `/assets/*.js` (404). Files are served at `/static/react/assets/`.
   * Dev server keeps base `/` so `npm run dev` works at localhost:5173.
   */
  base: command === 'build' ? '/static/react/' : '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(dirname, 'src'),
      react: reactRoot,
      'react-dom': reactDomRoot,
    },
    dedupe: ['react', 'react-dom', 'scheduler'],
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime'],
  },
  server: {
    port: 5173,
    strictPort: true,
    origin: 'http://localhost:5173',
  },
  build: {
    outDir: '../static/react',
    emptyOutDir: false, // Temporarily disabled to avoid permission issues on Windows
    manifest: true,
    rollupOptions: {
      input: {
        main: path.resolve(dirname, 'src/main.tsx'),
        'settings-dropdown': path.resolve(dirname, 'src/settings-dropdown.tsx'),
      },
      output: {
        /**
         * Without this, Rollup can split `react` across chunks; hooks then read a null dispatcher
         * (`Cannot read properties of null (reading 'useEffect')`). If a CDN blocks non-main chunk
         * names, whitelist `react-vendor-*.js` or serve all `static/react/assets/*`.
         */
        manualChunks: manualChunksReactVendor,
      },
    },
  },
  // Storybook test configuration commented out - uncomment if you need Storybook tests
  // test: {
  //   projects: [
  //     {
  //       extends: true,
  //       plugins: [
  //         storybookTest({
  //           configDir: path.join(dirname, '.storybook'),
  //         }),
  //       ],
  //       test: {
  //         name: 'storybook',
  //         browser: {
  //           enabled: true,
  //           headless: true,
  //           provider: playwright({}),
  //           instances: [
  //             {
  //               browser: 'chromium',
  //             },
  //           ],
  //         },
  //         setupFiles: ['.storybook/vitest.setup.ts'],
  //       },
  //     },
  //   ],
  // },
}));
