/**
 * Test setup file
 * 
 * This file runs before all tests to configure the test environment.
 */

import { beforeAll, afterAll } from 'vitest';

// Load environment variables for testing
import 'dotenv/config';

// Global test configuration
beforeAll(() => {
  // Suppress console output during tests unless DEBUG is set
  if (!process.env.DEBUG) {
    console.log = () => {};
    console.info = () => {};
  }
});

afterAll(() => {
  // Cleanup
});

// Increase timeout for LLM API calls
// Note: Individual tests can override this with their own timeout

