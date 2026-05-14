/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';

// Minimal Vitest setup. We use happy-dom (lighter than jsdom) because the store
// touches localStorage + window at module-load time but does not require a full
// browser environment. If we ever add React component tests (e.g. mounting via
// @testing-library/react), keep happy-dom — it's compatible.
export default defineConfig({
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    setupFiles: ['./src/test-setup.ts'],
  },
});
