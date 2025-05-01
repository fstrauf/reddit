import { Buffer } from 'node:buffer';

// --- Reddit Auth Token Cache (Simple In-Memory) ---
interface CachedToken {
  accessToken: string;
  expiresAt: number; // Timestamp (ms) when token expires
}
let tokenCache: CachedToken | null = null;
const TOKEN_EXPIRY_BUFFER = 60 * 1000; // Refresh token 1 minute before it expires

// --- Helper: Get Reddit App-Only Access Token ---
export async function getRedditAccessToken(config: any): Promise<string> {
  const now = Date.now();

  // Return cached token if valid
  if (tokenCache && tokenCache.expiresAt > now + TOKEN_EXPIRY_BUFFER) {
    return tokenCache.accessToken;
  }

  // Fetch new token if cache is invalid or missing
  const clientId = config.redditClientId; // Ensure NUXT_REDDIT_CLIENT_ID or REDDIT_CLIENT_ID is in .env
  const clientSecret = config.redditClientSecret; // Ensure NUXT_REDDIT_CLIENT_SECRET or REDDIT_CLIENT_SECRET is in .env

  if (!clientId || !clientSecret) {
    console.error('Reddit API credentials missing in runtime config');
    throw new Error('Reddit API credentials are not configured.'); // Throw plain error for util
  }

  const basicAuth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
  const tokenUrl = 'https://www.reddit.com/api/v1/access_token';

  try {
    console.log('Fetching new Reddit access token (from util)...');
    // Use global $fetch available in server utils
    const response = await $fetch<{ access_token: string; expires_in: number }>(tokenUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${basicAuth}`,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'RedditOutreachAutomator/0.1 by YourUsername' // Replace YourUsername or make dynamic
      },
      body: 'grant_type=client_credentials',
    });

    if (!response.access_token) {
      throw new Error('Failed to retrieve access token from Reddit.');
    }

    // Cache the new token
    tokenCache = {
      accessToken: response.access_token,
      expiresAt: now + (response.expires_in * 1000), // expires_in is in seconds
    };
    console.log('Successfully obtained and cached Reddit access token (from util).');
    return tokenCache.accessToken;

  } catch (error: any) {
    console.error('Error getting Reddit access token (in util):', error.data || error);
    // Rethrow a plain error
    throw new Error(`Failed to get Reddit access token: ${error.data?.message || error.message}`);
  }
}

// --- Reddit API Types (Simplified - can be shared or moved) ---
export interface RedditRule {
  kind: string;
  short_name: string;
  description: string;
  // Add other fields if needed
}

export interface RedditRulesResponse {
  rules: RedditRule[];
} 