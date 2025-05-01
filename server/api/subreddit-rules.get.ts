// This file might become obsolete if rules are always fetched in analyze-article
// Keeping it for now, but removing the duplicated helper function and types.

import { getRedditAccessToken, type RedditRule, type RedditRulesResponse } from '../utils/reddit'; // Import from util

// Types are now imported from ../utils/reddit
// interface RedditRule { ... }
// interface RedditRulesResponse { ... }

// Helper function is now imported from ../utils/reddit
// async function getRedditAccessToken(config: any): Promise<string> { ... }

// --- API Route Handler ---
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event);
  const query = getQuery(event);
  const subredditName = query.name as string;

  if (!subredditName) {
    throw createError({
      statusCode: 400,
      statusMessage: `Missing subreddit name in query parameter (${subredditName}).`,
    });
  }

  try {
    const accessToken = await getRedditAccessToken(config);

    const rulesApiUrl = `https://oauth.reddit.com/r/${subredditName}/about/rules.json`;
    console.log(`Fetching rules for r/${subredditName}...`);

    const rulesResponse = await $fetch<RedditRulesResponse>(rulesApiUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'User-Agent': 'RedditOutreachAutomator/0.1 by YourUsername' // Replace YourUsername or make dynamic
      },
    });

    console.log(`Successfully fetched rules for r/${subredditName}.`);
    return { rules: rulesResponse.rules || [] }; 

  } catch (error: any) {
    const statusCode = error.response?.status || error.statusCode || 500;
    const message = error.data?.message || error.message || 'Failed to fetch subreddit rules.';
    console.error(`Error fetching rules for r/${subredditName}:`, error.data || error);

    throw createError({
        statusCode: statusCode,
        statusMessage: message,
    });
  }
}); 