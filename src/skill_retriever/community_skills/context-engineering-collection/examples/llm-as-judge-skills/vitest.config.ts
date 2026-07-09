import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts', 'tests/**/*.test.ts'],
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'dist/', '**/*.test.ts', 'tests/setup.ts']
    },
    testTimeout: 60000, // 60s for LLM calls
    hookTimeout: 30000,
    // Retry failed tests once (helpful for flaky LLM calls)
    retry: 1
  }
});

