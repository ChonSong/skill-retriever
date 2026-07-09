import 'dotenv/config';

export const config = {
  openai: {
    apiKey: process.env.OPENAI_API_KEY || '',
    model: process.env.OPENAI_MODEL || 'gpt-4o'
  },
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY || ''
  }
} as const;

export function validateConfig(): void {
  if (!config.openai.apiKey) {
    throw new Error('OPENAI_API_KEY is required. Create a .env file with your API key.');
  }
}

