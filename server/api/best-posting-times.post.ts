import { getRedditAccessToken } from '../utils/reddit';

// --- Interfaces --- 
interface RequestBody {
    subreddits: string[];
}

interface RedditPost {
    kind: string;
    data: {
        name: string;
        score: number;
        created_utc: number;
        // Add other fields if needed
    };
}

interface RedditTopResponse {
    kind: string;
    data: {
        children: RedditPost[];
        after: string | null;
        before: string | null;
    };
}

interface TimeSlotData {
    totalScore: number;
    count: number;
    avgScore?: number; // To be calculated later
}

interface TimeAnalysis {
    // dayOfWeek (0=Sun, 6=Sat) -> hourOfDay (0-23 UTC) -> data
    byTime: Record<number, Record<number, TimeSlotData>>;
}

interface BestTimeSlot {
    day: number; // 0-6
    hour: number; // 0-23 UTC
    avgScore: number;
}

type BestTimesResponse = Record<string, { bestTimes?: BestTimeSlot[]; error?: string }>;

// --- Constants --- 
const POST_LIMIT = 50; // Number of top posts to fetch per subreddit
const TIME_PERIOD = 'month'; // Time period for top posts ('hour', 'day', 'week', 'month', 'year', 'all')
const TOP_SLOTS_COUNT = 3; // Number of best time slots to return
const MIN_POSTS_FOR_AVG = 3; // Minimum posts needed in a slot to calculate a reliable average

// --- Helper: Analyze Posts for Best Times --- 
function analyzePostTimes(posts: RedditPost[]): BestTimeSlot[] {
    const analysis: TimeAnalysis = { byTime: {} };

    posts.forEach(post => {
        if (!post.data || typeof post.data.created_utc !== 'number' || typeof post.data.score !== 'number') return;

        const date = new Date(post.data.created_utc * 1000); // Convert seconds to ms
        const dayOfWeek = date.getUTCDay();
        const hourOfDay = date.getUTCHours();
        const score = post.data.score;

        // Initialize day/hour slots if they don't exist
        if (!analysis.byTime[dayOfWeek]) analysis.byTime[dayOfWeek] = {};
        if (!analysis.byTime[dayOfWeek][hourOfDay]) {
            analysis.byTime[dayOfWeek][hourOfDay] = { totalScore: 0, count: 0 };
        }

        // Aggregate score and count
        analysis.byTime[dayOfWeek][hourOfDay].totalScore += score;
        analysis.byTime[dayOfWeek][hourOfDay].count++;
    });

    // Calculate averages and flatten into a list
    const slots: BestTimeSlot[] = [];
    for (const day in analysis.byTime) {
        for (const hour in analysis.byTime[day]) {
            const slotData = analysis.byTime[day][hour];
            if (slotData.count >= MIN_POSTS_FOR_AVG) { // Only consider slots with enough data
                slots.push({
                    day: parseInt(day),
                    hour: parseInt(hour),
                    avgScore: slotData.totalScore / slotData.count,
                });
            }
        }
    }

    // Sort by average score (descending) and take top N
    slots.sort((a, b) => b.avgScore - a.avgScore);
    return slots.slice(0, TOP_SLOTS_COUNT);
}

// --- API Route Handler --- 
export default defineEventHandler(async (event): Promise<BestTimesResponse> => {
    const config = useRuntimeConfig(event);
    const body = await readBody<RequestBody>(event);

    if (!body || !Array.isArray(body.subreddits) || body.subreddits.length === 0) {
        throw createError({ statusCode: 400, statusMessage: 'Missing or invalid \'subreddits\' array in request body.' });
    }

    const results: BestTimesResponse = {};
    let accessToken: string;

    try {
        accessToken = await getRedditAccessToken(config);
    } catch (error: any) {
        console.error('Failed to get Reddit token for time analysis:', error);
        // Return error for all subs if token fails
        body.subreddits.forEach(sub => {
            results[sub] = { error: `Failed to authenticate with Reddit: ${error.message}` };
        });
        return results;
    }

    // Process subreddits sequentially to reduce concurrent load / rate limit risk
    for (const subreddit of body.subreddits) {
        const subName = subreddit.replace(/^r\//, '');
        const apiUrl = `https://oauth.reddit.com/r/${subName}/top.json?t=${TIME_PERIOD}&limit=${POST_LIMIT}`;
        console.log(`Fetching top posts for r/${subName} for time analysis...`);

        try {
            const response = await $fetch<RedditTopResponse>(apiUrl, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'User-Agent': 'RedditOutreachAutomator/0.1 by YourUsername' // Use consistent User-Agent
                },
                ignoreResponseError: true, // Handle errors manually
            });
            
            // Basic check on response structure
            if (!response || !response.data || !Array.isArray(response.data.children)) {
                 // Handle cases like invalid subreddit (often 404) or unexpected format
                 console.warn(`Invalid response or no posts found for r/${subName}`);
                 // Check if $fetch threw an error object with status 
                 // Note: with ignoreResponseError, $fetch might still throw for network issues,
                 // but usually puts error details in the response object for HTTP errors.
                 const errorStatus = (response as any)?.status || (response as any)?._data?.status; // Heuristics
                 if (errorStatus === 404) {
                     throw new Error(`Subreddit r/${subName} not found.`);
                 } else if (errorStatus) {
                     throw new Error(`API error ${errorStatus} for r/${subName}.`);
                 } else {
                      throw new Error(`Invalid response structure or no posts found for r/${subName}.`);
                 }
            }

            if (response.data.children.length === 0) {
                 console.log(`No posts returned for r/${subName} in the last ${TIME_PERIOD}.`);
                 results[subName] = { bestTimes: [] }; // Indicate no data found
                 continue; // Skip to next subreddit
            }

            // Analyze the post times
            const bestTimes = analyzePostTimes(response.data.children);
            results[subreddit] = { bestTimes }; // Store result with original name (e.g., r/...) 
            console.log(`Successfully analyzed times for r/${subName}. Found ${bestTimes.length} potential slots.`);

            // Optional: Add a small delay between requests to be nicer to the API
            await new Promise(resolve => setTimeout(resolve, 250)); // 250ms delay

        } catch (error: any) {
            console.error(`Error processing subreddit r/${subName} for time analysis:`, error);
            results[subreddit] = { error: error.message || 'Failed to analyze posting times.' };
        }
    }

    console.log('Finished best posting time analysis.');
    return results;
}); 