import { OpenAI } from 'openai';
import { getRedditAccessToken } from '../utils/reddit';

// Define the expected request body structure
interface RequestBody {
  subreddit: string;
  limit: number;
}

// Reddit API response types
interface RedditPost {
  data: {
    title: string;
    selftext: string;
    score: number;
    num_comments: number;
    created_utc: number;
    url: string;
    id: string;
    author: string;
    subreddit: string;
  };
}

interface RedditComment {
  data: {
    body: string;
    score: number;
    created_utc: number;
    author: string;
    id: string;
  };
}

interface RedditListing {
  data: {
    children: RedditPost[];
    after: string;
  };
}

interface RedditCommentsResponse {
  data: {
    children: RedditComment[];
  };
}

// Analysis result types
interface BusinessOpportunity {
  title: string;
  description: string;
  keywords: string[];
  frequency: number;
  marketSize: string;
}

interface CommonProblem {
  title: string;
  description: string;
  keywords: string[];
  frequency: number;
  sentiment: string;
}

interface TrendingTopic {
  title: string;
  keywords: string[];
  frequency: number;
  sentiment: string;
}

interface SentimentBreakdown {
  positive: number;
  neutral: number;
  negative: number;
}

interface AnalysisResult {
  totalPosts: number;
  businessOpportunities: BusinessOpportunity[];
  commonProblems: CommonProblem[];
  trendingTopics: TrendingTopic[];
  sentimentBreakdown: SentimentBreakdown;
  averageSentiment: string;
}

// Helper function to fetch Reddit posts
async function fetchRedditPosts(subreddit: string, limit: number, accessToken: string): Promise<RedditPost[]> {
  const url = `https://oauth.reddit.com/r/${subreddit}/hot.json?limit=${limit}`;
  
  try {
    const response = await $fetch<RedditListing>(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'User-Agent': 'RedditSentimentAnalyzer/1.0'
      }
    });

    return response.data.children;
  } catch (error: any) {
    console.error(`Error fetching posts from r/${subreddit}:`, error);
    throw new Error(`Failed to fetch posts from r/${subreddit}: ${error.message}`);
  }
}

// Helper function to fetch comments for a post
async function fetchPostComments(subreddit: string, postId: string, accessToken: string): Promise<RedditComment[]> {
  const url = `https://oauth.reddit.com/r/${subreddit}/comments/${postId}.json?limit=50`;
  
  try {
    const response = await $fetch<RedditCommentsResponse[]>(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'User-Agent': 'RedditSentimentAnalyzer/1.0'
      }
    });

    // Reddit comments endpoint returns an array where the second element contains comments
    if (response.length > 1 && response[1].data.children) {
      return response[1].data.children.filter(comment => 
        comment.data.body && 
        comment.data.body !== '[deleted]' && 
        comment.data.body !== '[removed]'
      );
    }
    
    return [];
  } catch (error: any) {
    console.error(`Error fetching comments for post ${postId}:`, error);
    return []; // Return empty array on error, don't fail the whole analysis
  }
}

export default defineEventHandler(async (event): Promise<AnalysisResult> => {
  const config = useRuntimeConfig(event);
  const body = await readBody<RequestBody>(event);

  if (!body || !body.subreddit) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing subreddit name in request body',
    });
  }

  const subreddit = body.subreddit.replace(/^r\//, ''); // Remove r/ prefix if present
  const limit = Math.min(body.limit || 50, 100); // Cap at 100 posts

  // Get Reddit access token
  let accessToken: string;
  try {
    accessToken = await getRedditAccessToken(config);
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to authenticate with Reddit: ${error.message}`,
    });
  }

  // Fetch Reddit posts
  let posts: RedditPost[];
  try {
    console.log(`Fetching ${limit} posts from r/${subreddit}...`);
    posts = await fetchRedditPosts(subreddit, limit, accessToken);
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: error.message,
    });
  }

  if (posts.length === 0) {
    throw createError({
      statusCode: 404,
      statusMessage: `No posts found in r/${subreddit} or subreddit doesn't exist`,
    });
  }

  // Fetch comments for top posts (limit to first 10 posts to avoid rate limits)
  console.log('Fetching comments for top posts...');
  const topPosts = posts.slice(0, Math.min(10, posts.length));
  const allComments: RedditComment[] = [];

  for (const post of topPosts) {
    const comments = await fetchPostComments(subreddit, post.data.id, accessToken);
    allComments.push(...comments.slice(0, 20)); // Limit to 20 comments per post
    
    // Add a small delay to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  // Prepare content for OpenAI analysis
  const postsText = posts.map(post => 
    `Title: ${post.data.title}\nContent: ${post.data.selftext || 'No content'}\nScore: ${post.data.score}\n---`
  ).join('\n');

  const commentsText = allComments.slice(0, 200).map(comment => // Limit to 200 comments
    `Comment: ${comment.data.body}\nScore: ${comment.data.score}\n---`
  ).join('\n');

  // Analyze with OpenAI
  const openaiApiKey = config.openaiApiKey;
  if (!openaiApiKey) {
    throw createError({
      statusCode: 500,
      statusMessage: 'OpenAI API key is not configured.',
    });
  }

  const openai = new OpenAI({
    apiKey: openaiApiKey,
  });

  try {
    console.log('Analyzing content with OpenAI...');
    
    // Limit content length to avoid exceeding token limits
    const maxContentLength = 12000;
    const contentForAnalysis = (postsText + '\n\n' + commentsText).substring(0, maxContentLength);

    const prompt = `Analyze the following Reddit posts and comments from r/${subreddit} to identify business opportunities, common problems, trending topics, and sentiment. Provide the output as a JSON object with the following structure:

{
  "businessOpportunities": [
    {
      "title": "Opportunity title",
      "description": "Detailed description of the business opportunity",
      "keywords": ["keyword1", "keyword2"],
      "frequency": 5,
      "marketSize": "Small/Medium/Large"
    }
  ],
  "commonProblems": [
    {
      "title": "Problem title",
      "description": "Detailed description of the problem",
      "keywords": ["keyword1", "keyword2"],
      "frequency": 10,
      "sentiment": "Negative/Neutral/Positive"
    }
  ],
  "trendingTopics": [
    {
      "title": "Topic title",
      "keywords": ["keyword1", "keyword2"],
      "frequency": 8,
      "sentiment": "Negative/Neutral/Positive"
    }
  ],
  "sentimentBreakdown": {
    "positive": 30,
    "neutral": 50,
    "negative": 20
  },
  "averageSentiment": "Neutral"
}

Focus on:
1. Business opportunities that could solve recurring problems
2. Common pain points that appear multiple times
3. Topics that generate significant discussion
4. Overall sentiment trends

Reddit Content:
${contentForAnalysis}`;

    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" },
      temperature: 0.3,
    });

    const resultJson = completion.choices[0]?.message?.content;
    if (!resultJson) {
      throw new Error('OpenAI response content is empty.');
    }

    let analysisData;
    try {
      analysisData = JSON.parse(resultJson);
    } catch (parseError: any) {
      console.error("Failed to parse OpenAI JSON response:", resultJson);
      throw new Error(`Failed to parse OpenAI response: ${parseError.message}`);
    }

    // Construct final result
    const result: AnalysisResult = {
      totalPosts: posts.length,
      businessOpportunities: analysisData.businessOpportunities || [],
      commonProblems: analysisData.commonProblems || [],
      trendingTopics: analysisData.trendingTopics || [],
      sentimentBreakdown: analysisData.sentimentBreakdown || { positive: 0, neutral: 0, negative: 0 },
      averageSentiment: analysisData.averageSentiment || 'Unknown'
    };

    console.log(`Analysis complete for r/${subreddit}: ${result.businessOpportunities.length} opportunities, ${result.commonProblems.length} problems found`);
    
    return result;

  } catch (error: any) {
    console.error('Error calling OpenAI API:', error);
    const errorMessage = error.response?.data?.error?.message || error.message || 'Unknown OpenAI error';
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to analyze content with OpenAI: ${errorMessage}`,
    });
  }
});
