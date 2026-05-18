// Minimal vitest config for Task 0.2 smoke test.
// Task 0.5 will replace/extend this with full configuration.
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'node',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
