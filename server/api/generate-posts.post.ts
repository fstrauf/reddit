import { OpenAI } from 'openai';
import * as cheerio from 'cheerio';
import type { RedditRule } from '../utils/reddit'; // Import rule type

// --- Interfaces --- 

// Expected structure from the analyze-article step
interface AnalysisResultData {
  themes: string[];
  keywords: string[];
  suggestedSubreddits: string[];
}
type RulesData = Record<string, RedditRule[] | { error: string }>;

// Expected request body for this endpoint
interface GeneratePostsRequestBody {
  articleUrl: string; // Need URL to re-fetch content reliably
  analysis: AnalysisResultData;
  rules: RulesData;
}

// Structure for a single post suggestion
interface PostSuggestion {
    title: string;
    body: string;
}

// Structure for the response of this endpoint
type PostSuggestionsResponse = Record<string, PostSuggestion | { error: string }>;

// --- Helper: Fetch and Parse Article Content (Duplicated for now, consider refactoring) ---
async function fetchAndParseArticle(url: string): Promise<string> {
    console.log(`(GeneratePosts) Fetching content for ${url}`);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Fetch failed: ${response.status} ${response.statusText}`);
    }
    const html = await response.text();
    const $ = cheerio.load(html);
    let contentElement = $('.available-content, article').first();
    if (!contentElement.length) contentElement = $('body');
    const articleText = contentElement.text().replace(/\s\s+/g, ' ').trim();
    if (!articleText) {
      throw new Error('Could not extract meaningful content from the URL.');
    }
    console.log(`(GeneratePosts) Successfully extracted ~${articleText.length} characters.`);
    return articleText;
}

// --- API Route Handler ---
export default defineEventHandler(async (event): Promise<PostSuggestionsResponse> => {
  const config = useRuntimeConfig(event);
  const body = await readBody<GeneratePostsRequestBody>(event);

  if (!body || !body.articleUrl || !body.analysis || !body.rules) {
    throw createError({ statusCode: 400, statusMessage: 'Missing required fields in request body.' });
  }

  const { articleUrl, analysis, rules } = body;
  const suggestions: PostSuggestionsResponse = {};

  // --- 1. Re-fetch Article Content --- 
  let articleText = '';
  try {
     articleText = await fetchAndParseArticle(articleUrl);
  } catch (error: any) {
     console.error('Error re-fetching article content:', error);
     // Return error for all suggestions if article fetch fails
     analysis.suggestedSubreddits.forEach(sub => {
        suggestions[sub] = { error: `Failed to fetch article content: ${error.message}` };
     });
     return suggestions; // Early return
  }
  
  // --- 2. Initialize OpenAI Client --- 
  const openaiApiKey = config.openaiApiKey;
  if (!openaiApiKey) {
     // Should generally not happen if analyze worked, but check anyway
      analysis.suggestedSubreddits.forEach(sub => {
        suggestions[sub] = { error: 'OpenAI API key is not configured on the server.' };
     });
     return suggestions; // Early return
  }
  const openai = new OpenAI({ apiKey: openaiApiKey });

  // --- 3. Generate Suggestions Concurrently --- 
  const suggestionPromises = analysis.suggestedSubreddits.map(async (subreddit) => {
    const subredditRules = rules[subreddit];
    let suggestion: PostSuggestion | { error: string };

    // Check if we have valid rules for this subreddit
    if (!subredditRules || 'error' in subredditRules) {
      suggestion = { error: `Rules unavailable or failed to fetch for ${subreddit}: ${subredditRules?.error || 'Unknown error'}` };
    } else {
      try {
        console.log(`Generating post suggestion for ${subreddit}...`);
        const maxContentLength = 6000; // Leave room for rules/prompt
        const contentSnippet = articleText.substring(0, maxContentLength);
        const rulesString = subredditRules.map(r => `- ${r.short_name}: ${r.description || 'No description.'}`).join('\n');

        const prompt = 
`Based on the following article content, themes, keywords, and the rules for the specific subreddit, generate a suitable Reddit post (title and body) to promote the article there. The goal is organic promotion and discussion, not spam. Ensure the post complies with the provided rules.

**Article Content Snippet:**
${contentSnippet}

**Main Themes:**
${analysis.themes.join(', ')}

**Keywords:**
${analysis.keywords.join(', ')}

**Subreddit:**
${subreddit}

**Subreddit Rules:**
${rulesString || 'No specific rules provided.'}

**Instructions:**
- Create a compelling title that fits Reddit's style for the target subreddit.
- Write a post body that summarizes the key points or a relevant aspect of the article, encourages discussion, and only includes the article link if that is an ok thing to do in the subreddit: ${articleUrl}
- Adhere strictly to the subreddit rules provided above. If rules prohibit links or self-promotion, adapt the post accordingly (e.g., focus on discussion points without a direct link, or state that a link can be provided if requested).
- Output *only* a valid JSON object containing two keys: "title" (string) and "body" (string). Do not include any other text or explanations before or after the JSON object.
- If the subreddit rules prohibit links, do not include the article link in the post body.
- If the subreddit rules prohibit self-promotion, do not include the article link in the post body.
- Make the text sound natural and human-like, not sales-y or promotional. Base the writing on the article content, not on the title.
- Avoid being spammy or promotional.
- Avoid using clickbait titles.
- Avoid using sensationalist language.
- Avoid any groundbreaking, overly excited, or promotional language.
- 

**JSON Output:**`;

        const completion = await openai.chat.completions.create({
          model: "gpt-4o-mini", 
          messages: [{ role: "user", content: prompt }],
          response_format: { type: "json_object" }, 
          temperature: 0.5, // Slightly higher temperature for more creative suggestions
        });

        const resultJson = completion.choices[0]?.message?.content;
        if (!resultJson) {
          throw new Error('OpenAI response content is empty.');
        }
        
        const parsedResult = JSON.parse(resultJson);
        if (!parsedResult || typeof parsedResult.title !== 'string' || typeof parsedResult.body !== 'string') {
           throw new Error('OpenAI response is not in the expected JSON format {title: string, body: string}.');
        }
        suggestion = parsedResult as PostSuggestion;
        console.log(`Successfully generated suggestion for ${subreddit}.`);

      } catch (error: any) {
         console.error(`Error generating suggestion for ${subreddit}:`, error);
         suggestion = { error: `OpenAI generation failed: ${error.message}` };
      }
    }
    return { subreddit, suggestion };
  });

  // Wait for all suggestions to complete
  const results = await Promise.allSettled(suggestionPromises);

  // Aggregate results
  results.forEach(result => {
    if (result.status === 'fulfilled') {
      suggestions[result.value.subreddit] = result.value.suggestion;
    } else {
      // This should ideally not happen if errors are caught within the map
      console.error('Unexpected error in Promise.allSettled for suggestions:', result.reason);
      // Find the subreddit if possible (difficult here) or add a generic error
    }
  });

  return suggestions;
}); 