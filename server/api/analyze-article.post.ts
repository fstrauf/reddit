import { OpenAI } from 'openai';
import * as cheerio from 'cheerio';
import { getRedditAccessToken, type RedditRule, type RedditRulesResponse } from '../utils/reddit'; // Import Reddit utils

// Define the expected request body structure
interface RequestBody {
  url: string;
}

// Define the expected OpenAI analysis response structure
interface OpenAIAnalysis {
  themes: string[];
  keywords: string[];
  suggestedSubreddits: string[];
}

// Type for the final combined response
interface CombinedAnalysisResponse {
  analysis: OpenAIAnalysis;
  rules: Record<string, RedditRule[] | { error: string }>; // Map subreddit name to its rules or an error object
}

// --- Helper to Fetch Rules for a Single Subreddit ---
async function fetchRulesForSubreddit(subreddit: string, accessToken: string): Promise<RedditRule[]> {
  const subName = subreddit.replace(/^r\//, '');
  const rulesApiUrl = `https://oauth.reddit.com/r/${subName}/about/rules.json`;
  console.log(`Fetching rules for r/${subName} (within analyze)...`);
  try {
    const rulesResponse = await $fetch<RedditRulesResponse>(rulesApiUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'User-Agent': 'RedditOutreachAutomator/0.1 by YourUsername' // Use consistent User-Agent
      },
      // Ignore response status code errors for individual fetches (we handle errors below)
      ignoreResponseError: true, 
    });
    // Check for explicit error structure or empty/invalid response if needed
    if (rulesResponse && Array.isArray(rulesResponse.rules)) {
        return rulesResponse.rules;
    } else {
        console.warn(`No rules found or invalid format for r/${subName}`);
        return []; // Return empty array if no rules found or invalid format
    }
  } catch (error: any) {
     // This catch might not be strictly necessary with ignoreResponseError: true,
     // but kept for robustness. $fetch might throw for network errors etc.
    console.error(`Error fetching rules for r/${subName} (within analyze):`, error.data || error);
    throw new Error(`Failed to fetch rules for ${subreddit}: ${error.data?.message || error.message}`); // Re-throw to be caught by Promise.allSettled
  }
}

export default defineEventHandler(async (event): Promise<CombinedAnalysisResponse> => {
  // Get runtime configuration (includes .env variables)
  const config = useRuntimeConfig(event);

  // Read the request body
  const body = await readBody<RequestBody>(event);

  if (!body || !body.url) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing article URL in request body',
    });
  }

  const articleUrl = body.url;

  // --- 1. Fetch and Parse Article Content --- 
  let articleText = '';
  try {
    console.log(`Fetching content for ${articleUrl}`);
    const response = await fetch(articleUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch article: ${response.status} ${response.statusText}`);
    }
    const html = await response.text();
    const $ = cheerio.load(html);

    // Attempt to find common Substack article body selectors
    let contentElement = $('.available-content'); // Common selector
    if (!contentElement.length) {
        contentElement = $('article'); // Fallback to article tag
    }
    if (!contentElement.length) {
        contentElement = $('body'); // Final fallback to body
    }

    // Extract text, clean up whitespace
    articleText = contentElement.text().replace(/\s\s+/g, ' ').trim();

    if (!articleText) {
      throw new Error('Could not extract meaningful content from the URL.');
    }
    console.log(`Successfully extracted ~${articleText.length} characters.`);

  } catch (error: any) {
    console.error('Error fetching or parsing article:', error);
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to process article URL: ${error.message}`,
    });
  }

  console.log(config);
  // --- 2. Analyze with OpenAI --- 
  const openaiApiKey = config.openaiApiKey; // Nuxt automatically maps OPENAI_API_KEY

  if (!openaiApiKey) {
    throw createError({
      statusCode: 500,
      statusMessage: 'OpenAI API key is not configured.',
    });
  }

  const openai = new OpenAI({
    apiKey: openaiApiKey,
  });

  let analysis: OpenAIAnalysis = { themes: [], keywords: [], suggestedSubreddits: [] };
  try {
    console.log('Calling OpenAI to analyze content and suggest subreddits...');
    // Limit content length to avoid exceeding token limits (adjust as needed)
    const maxContentLength = 8000; // Approx character limit for ~4k tokens 
    const contentForAnalysis = articleText.substring(0, maxContentLength);

    const prompt = 
`Analyze the following article content. Provide the output as a single JSON object with three keys:
1. 'themes': An array of strings identifying 3-5 main themes discussed.
2. 'keywords': An array of strings listing 5-10 specific and relevant keywords/terms for finding online communities.
3. 'suggestedSubreddits': An array of strings suggesting 5-10 relevant Reddit subreddits (including the 'r/' prefix, e.g., 'r/programming') where this article might be suitable for discussion, based on the content, themes, and keywords. Suggest smaller subreddits, not large one.

Article Content:
${contentForAnalysis}`;

    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini", // Or gpt-3.5-turbo, gpt-4o etc.
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" }, 
      temperature: 0.2, // Lower temperature for more deterministic output
    });

    const resultJson = completion.choices[0]?.message?.content;

    if (!resultJson) {
      throw new Error('OpenAI response content is empty.');
    }

    // Safely parse the JSON response
    try {
        const parsedResult = JSON.parse(resultJson);
        // Updated validation for the new structure
        if (parsedResult && 
            Array.isArray(parsedResult.themes) && 
            Array.isArray(parsedResult.keywords) &&
            Array.isArray(parsedResult.suggestedSubreddits)) {
             analysis = parsedResult as OpenAIAnalysis;
        } else {
            console.error("Parsed JSON does not match expected structure:", parsedResult);
            throw new Error('OpenAI response is not in the expected JSON format (themes, keywords, suggestedSubreddits arrays).')
        }
    } catch (parseError: any) {
        console.error("Failed to parse OpenAI JSON response:", resultJson);
        throw new Error(`Failed to parse OpenAI response: ${parseError.message}`);
    }

    console.log('OpenAI analysis successful:', analysis);

  } catch (error: any) {
    console.error('Error calling OpenAI API:', error);
    const errorMessage = error.response?.data?.error?.message || error.message || 'Unknown OpenAI error';
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to analyze article with OpenAI: ${errorMessage}`,
    });
  }

  // --- 3. Fetch Subreddit Rules Concurrently --- 
  const rulesMap: Record<string, RedditRule[] | { error: string }> = {};
  if (analysis.suggestedSubreddits && analysis.suggestedSubreddits.length > 0) {
    try {
      console.log('Fetching Reddit auth token for rules...');
      const accessToken = await getRedditAccessToken(config);
      console.log(`Fetching rules for: ${analysis.suggestedSubreddits.join(', ')}`);
      
      // Map each subreddit to a promise that fetches its rules
      const rulePromises = analysis.suggestedSubreddits.map(sub => 
        fetchRulesForSubreddit(sub, accessToken) // Directly return the promise from fetchRulesForSubreddit
      );

      // Use Promise.allSettled to wait for all fetches
      const results = await Promise.allSettled(rulePromises);

      // Process results, associating them back to the original subreddit names
      results.forEach((result, index) => {
        const subreddit = analysis.suggestedSubreddits[index]; // Get corresponding subreddit name
        if (result.status === 'fulfilled') {
          // Successfully fetched rules
          rulesMap[subreddit] = result.value; // result.value is RedditRule[]
        } else {
          // Failed to fetch rules for this specific subreddit
          console.error(`Failed rule fetch for ${subreddit}:`, result.reason);
          rulesMap[subreddit] = { error: result.reason?.message || 'Failed to fetch rules' };
        }
      });
      console.log('Finished fetching all subreddit rules.');

    } catch (error: any) {
      // Handle errors from getRedditAccessToken or Promise.allSettled setup
      console.error('Error during batch rule fetching process:', error);
      // Optionally add error indicators for all subs if token fails
      analysis.suggestedSubreddits.forEach(sub => rulesMap[sub] = { error: `Rule fetching failed: ${error.message}` });
    }
  }

  // --- 4. Return Combined Result --- 
  return {
    analysis,
    rules: rulesMap,
  };
}); 