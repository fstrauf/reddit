<template>
  <div class="min-h-screen bg-gray-100 py-10 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto bg-white p-6 sm:p-8 rounded-lg shadow-lg">
      <h1 class="text-3xl font-bold mb-8 text-center text-gray-800">Reddit Sentiment Analyzer</h1>
      <p class="text-center text-gray-600 mb-8">Discover business opportunities by analyzing sentiment and common problems in Reddit communities</p>

      <!-- Subreddit Analysis Section -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Left: Subreddit Input -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">1. Analyze Subreddit</h2>
          <form @submit.prevent="analyzeSubreddit">
            <div class="mb-4">
              <label for="subreddit-name" class="block text-sm font-medium text-gray-700 mb-1">Subreddit Name</label>
              <div class="flex">
                <span class="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">r/</span>
                <input
                  type="text"
                  id="subreddit-name"
                  v-model="subredditName"
                  placeholder="PersonalFinanceNZ"
                  required
                  :disabled="isAnalyzing"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-r-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
                />
              </div>
            </div>
            <div class="mb-4">
              <label for="post-limit" class="block text-sm font-medium text-gray-700 mb-1">Number of Posts to Analyze</label>
              <select
                id="post-limit"
                v-model="postLimit"
                :disabled="isAnalyzing"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
              >
                <option value="25">25 posts</option>
                <option value="50">50 posts</option>
                <option value="100">100 posts</option>
              </select>
            </div>
            <button
              type="submit"
              :disabled="isAnalyzing"
              class="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center justify-center transition duration-150 ease-in-out"
            >
              <span v-if="!isAnalyzing">Analyze Sentiment & Find Opportunities</span>
              <span v-else class="flex items-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ loadingMessage }}
              </span>
            </button>
            
            <!-- Analysis Loading Text -->
            <div v-if="isAnalyzing" class="text-center pt-4 text-sm text-gray-500">
              {{ loadingMessage }}
            </div>
            
            <!-- Analysis Error Display -->
            <div v-if="analysisError && !isAnalyzing" class="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
              <p class="font-medium">Analysis Error:</p>
              <p>{{ analysisError }}</p>
            </div>
          </form>
        </div>

        <!-- Right: Quick Stats -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">Analysis Overview</h2>
          <div v-if="!analysisResult && !isAnalyzing" class="text-sm text-gray-500 italic">
            Analysis results will appear here after analyzing a subreddit.
          </div>
          <div v-if="analysisResult" class="space-y-4">
            <div class="bg-blue-50 p-4 rounded-lg">
              <h3 class="font-medium text-blue-800 mb-2">Posts Analyzed</h3>
              <p class="text-2xl font-bold text-blue-600">{{ analysisResult.totalPosts }}</p>
            </div>
            <div class="bg-green-50 p-4 rounded-lg">
              <h3 class="font-medium text-green-800 mb-2">Business Opportunities Found</h3>
              <p class="text-2xl font-bold text-green-600">{{ analysisResult.businessOpportunities?.length || 0 }}</p>
            </div>
            <div class="bg-purple-50 p-4 rounded-lg">
              <h3 class="font-medium text-purple-800 mb-2">Common Problems</h3>
              <p class="text-2xl font-bold text-purple-600">{{ analysisResult.commonProblems?.length || 0 }}</p>
            </div>
            <div class="bg-orange-50 p-4 rounded-lg">
              <h3 class="font-medium text-orange-800 mb-2">Average Sentiment</h3>
              <p class="text-2xl font-bold text-orange-600">{{ analysisResult.averageSentiment || 'N/A' }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Results Section -->
      <div v-if="analysisResult" class="space-y-8">
        <!-- Business Opportunities -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">💡 Business Opportunities</h2>
          <div v-if="analysisResult.businessOpportunities?.length" class="space-y-4">
            <div v-for="(opportunity, index) in analysisResult.businessOpportunities" :key="index" class="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 class="font-semibold text-green-800 mb-2">{{ opportunity.title }}</h3>
              <p class="text-green-700 mb-2">{{ opportunity.description }}</p>
              <div class="flex flex-wrap gap-2 mb-2">
                <span v-for="keyword in opportunity.keywords" :key="keyword" class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  {{ keyword }}
                </span>
              </div>
              <p class="text-sm text-green-600">
                <strong>Frequency:</strong> {{ opportunity.frequency }} mentions
                <span class="mx-2">•</span>
                <strong>Potential Market Size:</strong> {{ opportunity.marketSize }}
              </p>
            </div>
          </div>
          <div v-else class="text-gray-500 italic">No business opportunities identified yet.</div>
        </div>

        <!-- Common Problems -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">🚨 Common Problems</h2>
          <div v-if="analysisResult.commonProblems?.length" class="space-y-4">
            <div v-for="(problem, index) in analysisResult.commonProblems" :key="index" class="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 class="font-semibold text-red-800 mb-2">{{ problem.title }}</h3>
              <p class="text-red-700 mb-2">{{ problem.description }}</p>
              <div class="flex flex-wrap gap-2 mb-2">
                <span v-for="keyword in problem.keywords" :key="keyword" class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  {{ keyword }}
                </span>
              </div>
              <p class="text-sm text-red-600">
                <strong>Frequency:</strong> {{ problem.frequency }} mentions
                <span class="mx-2">•</span>
                <strong>Sentiment:</strong> {{ problem.sentiment }}
              </p>
            </div>
          </div>
          <div v-else class="text-gray-500 italic">No common problems identified yet.</div>
        </div>

        <!-- Trending Topics -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">📈 Trending Topics</h2>
          <div v-if="analysisResult.trendingTopics?.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div v-for="(topic, index) in analysisResult.trendingTopics" :key="index" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 class="font-semibold text-blue-800 mb-2">{{ topic.title }}</h3>
              <div class="flex flex-wrap gap-1 mb-2">
                <span v-for="keyword in topic.keywords" :key="keyword" class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {{ keyword }}
                </span>
              </div>
              <p class="text-sm text-blue-600">
                <strong>Mentions:</strong> {{ topic.frequency }}
                <span class="mx-2">•</span>
                <strong>Sentiment:</strong> {{ topic.sentiment }}
              </p>
            </div>
          </div>
          <div v-else class="text-gray-500 italic">No trending topics identified yet.</div>
        </div>

        <!-- Sentiment Analysis -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">📊 Sentiment Analysis</h2>
          <div v-if="analysisResult.sentimentBreakdown" class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
              <h3 class="font-semibold text-green-800 mb-2">Positive</h3>
              <p class="text-3xl font-bold text-green-600">{{ analysisResult.sentimentBreakdown.positive }}%</p>
            </div>
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
              <h3 class="font-semibold text-yellow-800 mb-2">Neutral</h3>
              <p class="text-3xl font-bold text-yellow-600">{{ analysisResult.sentimentBreakdown.neutral }}%</p>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <h3 class="font-semibold text-red-800 mb-2">Negative</h3>
              <p class="text-3xl font-bold text-red-600">{{ analysisResult.sentimentBreakdown.negative }}%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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

const subredditName = ref('PersonalFinanceNZ');
const postLimit = ref('50');
const isAnalyzing = ref(false);
const loadingMessage = ref('');
const analysisError = ref('');
const analysisResult = ref<AnalysisResult | null>(null);

const analyzeSubreddit = async () => {
  if (!subredditName.value.trim()) {
    analysisError.value = 'Please enter a subreddit name';
    return;
  }

  isAnalyzing.value = true;
  analysisError.value = '';
  analysisResult.value = null;
  
  try {
    loadingMessage.value = 'Fetching posts from Reddit...';
    
    const response = await $fetch('/api/analyze-subreddit', {
      method: 'POST',
      body: {
        subreddit: subredditName.value.trim(),
        limit: parseInt(postLimit.value)
      }
    });

    analysisResult.value = response;
    
  } catch (error: any) {
    console.error('Analysis error:', error);
    analysisError.value = error.data?.message || error.message || 'Failed to analyze subreddit';
  } finally {
    isAnalyzing.value = false;
    loadingMessage.value = '';
  }
};

// Set page title
useHead({
  title: 'Reddit Sentiment Analyzer - Find Business Opportunities'
});
</script>
                                (No peak time found)
                            </span>
                            <!-- Add indicator if time analysis is still loading? Optional -->
                        </div>
                         <!-- Right side: Toggle text -->
                        <div>
                           <span class="text-xs text-gray-500 group-open:hidden">Show Details</span>
                           <span class="text-xs text-gray-500 hidden group-open:inline">Hide Details</span>
                        </div>
                    </summary>
                    <div class="border-t border-gray-200 p-4 space-y-4">
                        <!-- Best Times (Inside Details) -->
                        <div>
                            <h4 class="font-semibold mb-1 text-sm text-gray-700">Best Posting Times (Your Timezone: {{ localTimeZone || 'Unknown' }})</h4>
                            <p class="text-xs text-gray-500 mb-2">Based on average score of top ~{{ POST_LIMIT }} posts from the last month.</p> <!-- Explanation Added -->
                             <div v-if="bestTimesData && bestTimesData[subreddit] && bestTimesData[subreddit].error" class="text-red-600 text-xs">
                                Error: {{ bestTimesData[subreddit].error }}
                            </div>
                             <ul v-else-if="bestTimesData && bestTimesData[subreddit]?.bestTimes?.length" class="space-y-1 text-xs">
                                 <li v-for="(slot, i) in bestTimesData[subreddit]?.bestTimes" :key="i">
                                     {{ formatTimeToLocal(slot.day, slot.hour) }} 
                                     <span class="text-gray-500">(Avg Score: {{ slot.avgScore.toFixed(0) }})</span>
                                 </li>
                             </ul>
                             <p v-else-if="bestTimesData && bestTimesData[subreddit]" class="text-xs text-gray-500 italic">Not enough data/no peak times found.</p>
                              <p v-else class="text-xs text-gray-400 italic">
                                (Times loading or unavailable)
                             </p>
                        </div>
                        <!-- Rules -->
                        <div>
                             <h4 class="font-semibold mb-1 text-sm text-gray-700">Rules:</h4>
                             <div v-if="rulesData && rulesData[subreddit] && 'error' in rulesData[subreddit]" class="p-2 text-xs bg-red-100 border border-red-300 text-red-700 rounded">
                                <p class="font-bold">Error fetching rules:</p>
                                <p>{{ rulesData[subreddit].error }}</p>
                             </div>
                             <div v-else-if="rulesData && rulesData[subreddit]" class="text-xs space-y-1 text-gray-600">
                                <ul v-if="(rulesData[subreddit] as SubredditRule[]).length > 0" class="list-decimal list-inside space-y-1">
                                    <li v-for="(rule, index) in (rulesData[subreddit] as SubredditRule[])" :key="index">
                                        <strong class="font-medium text-gray-700">{{ rule.short_name }}</strong>
                                        <p v-if="rule.description" class="ml-4 text-gray-500">{{ rule.description }}</p>
                                    </li>
                                </ul>
                                <p v-else class="text-gray-500 italic">No rules listed via API.</p>
                            </div>
                             <div v-else class="text-xs text-gray-400 italic">
                                (Rules loading or unavailable)
                             </div>
                        </div>
                    </div>
                </details>
              </li>
            </ul>
          
          <!-- Generate Suggestions Button -->
           <div class="mt-6 pt-6 border-t border-gray-200 text-center">
                <button 
                  @click="generatePostSuggestions"
                  :disabled="isLoadingSuggestions || !analysisResult || !rulesData || isLoadingAnalysis || !!analysisError || !!timesError"
                  class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50 flex items-center justify-center mx-auto transition duration-150 ease-in-out"
                >
                   <span v-if="!isLoadingSuggestions">3. Generate Post Suggestions</span>
                   <span v-else class="flex items-center">
                      <svg class="animate-spin h-5 w-5 text-white mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      Generating...
                   </span>
               </button>
           </div>
      </div>
      
       <!-- Bottom Section: Generated Suggestions -->
       <div v-if="!isLoadingAnalysis">
           <!-- Suggestions Loading Indicator -->
           <div v-if="isLoadingSuggestions" class="text-center py-6">
             <p class="text-gray-600 flex items-center justify-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-green-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                Generating post suggestions via OpenAI...
             </p>
          </div>
          <!-- Suggestions Error Display -->
          <div v-if="suggestionsError && !isLoadingSuggestions" class="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
              <p class="font-bold">Suggestion Error:</p>
              <p>{{ suggestionsError }}</p>
          </div>
          <!-- Suggestions Display Grid -->
          <div v-if="postSuggestions && !isLoadingSuggestions" class="border border-gray-200 rounded-lg p-6">
              <h2 class="text-xl font-semibold mb-4 text-gray-700">4. Generated Post Suggestions</h2>
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                 <div v-for="(suggestion, sub) in postSuggestions" :key="sub" class="p-4 bg-gray-50 rounded border border-gray-100">
                     <h3 class="font-semibold mb-2 text-lg text-gray-800">{{ sub }}</h3>
                     <!-- Error Display for specific suggestion -->
                     <div v-if="'error' in suggestion" class="text-red-600 text-sm">
                         <strong>Error:</strong> {{ suggestion.error }}
                     </div>
                      <!-- Editable Title and Body -->
                      <div v-else class="space-y-3">
                         <div>
                             <label class="block font-medium text-sm text-gray-700">Title:</label>
                             <textarea 
                                 :value="suggestion.title" 
                                 rows="2" 
                                 class="w-full mt-1 px-2 py-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                                 @input="updateSuggestionTitle(sub as string, ($event.target as HTMLTextAreaElement).value)"
                             ></textarea>
                         </div>
                         <div>
                              <label class="block font-medium text-sm text-gray-700">Body:</label>
                             <textarea 
                                 :value="suggestion.body" 
                                 rows="8" 
                                 class="w-full mt-1 px-2 py-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                                 @input="updateSuggestionBody(sub as string, ($event.target as HTMLTextAreaElement).value)"
                             ></textarea>
                         </div>
                          <!-- Removed Submit Button -->
                     </div>
                 </div>
             </div>
          </div>
      </div>

    </div> <!-- End Max Width Container -->
  </div> <!-- End Outer Container -->
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// --- Interfaces --- 
interface AnalysisResultData {
  themes: string[];
  keywords: string[];
  suggestedSubreddits: string[];
}
interface SubredditRule {
    short_name: string;
    description: string;
    kind: string; 
}
type RulesData = Record<string, SubredditRule[] | { error: string }>;
interface CombinedAnalysisResponse {
    analysis: AnalysisResultData;
    rules: RulesData;
}
interface PostSuggestion {
    title: string;
    body: string;
}
type PostSuggestionsData = Record<string, PostSuggestion | { error: string }>;

interface BestTimeSlot {
    day: number; // 0-6
    hour: number; // 0-23 UTC
    avgScore: number;
}
type BestTimesData = Record<string, { bestTimes?: BestTimeSlot[]; error?: string }>;

// --- Constants (for display) --- 
// Match the value used in the API route for the explanation text
const POST_LIMIT = 50; 

// --- Reactive State --- 
const articleUrl = ref('')
const isLoadingAnalysis = ref(false)
const analysisResult = ref<AnalysisResultData | null>(null)
const rulesData = ref<RulesData | null>(null) 
const analysisError = ref<string | null>(null)

const isLoadingSuggestions = ref(false)
const postSuggestions = ref<PostSuggestionsData | null>(null)
const suggestionsError = ref<string | null>(null)

const bestTimesData = ref<BestTimesData | null>(null)
const timesError = ref<string | null>(null)
const localTimeZone = ref<string>('')

// --- Computed Loading Message ---
const loadingMessage = computed(() => {
    if (!isLoadingAnalysis.value) return ''
    if (!analysisResult.value) {
        return 'Fetching article, analyzing content, and retrieving rules...'
    } else {
        return 'Analyzing best posting times...'
    }
})

// --- Lifecycle Hook --- 
onMounted(() => {
    // Detect user's timezone after component mounts (client-side only)
    try {
        localTimeZone.value = Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch (e) {
        console.error("Could not detect timezone:", e);
        localTimeZone.value = 'UTC'; // Fallback
    }
});

// --- Methods --- 
const processArticle = async () => {
   isLoadingAnalysis.value = true
  analysisResult.value = null
  rulesData.value = null 
  analysisError.value = null
  postSuggestions.value = null 
  suggestionsError.value = null
  bestTimesData.value = null 
  timesError.value = null 
  
  try {
    const response = await $fetch<CombinedAnalysisResponse>('/api/analyze-article', {
      method: 'POST',
      body: { url: articleUrl.value },
    })
    analysisResult.value = response.analysis
    rulesData.value = response.rules

    // Step 2: Automatically analyze best times if analysis was successful
    if (analysisResult.value?.suggestedSubreddits && analysisResult.value.suggestedSubreddits.length > 0) {
        await findBestPostingTimes(); // Call the time analysis function
    }

  } catch (err: any) {
    console.error('Error during initial analysis/rule fetch:', err);
    analysisError.value = err.data?.message || err.message || 'An unknown error occurred during analysis.';
  } finally {
    isLoadingAnalysis.value = false;
  }
}

const generatePostSuggestions = async () => {
    if (!analysisResult.value || !rulesData.value) return;

    isLoadingSuggestions.value = true;
    postSuggestions.value = null;
    suggestionsError.value = null;

    console.log("Requesting suggestions with:", {
        articleUrl: articleUrl.value,
        analysis: analysisResult.value,
        rules: rulesData.value
    });

    try {
       const response = await $fetch<PostSuggestionsData>('/api/generate-posts', {
           method: 'POST',
           body: {
               articleUrl: articleUrl.value,
               analysis: analysisResult.value,
               rules: rulesData.value
           }
       });
       postSuggestions.value = response;
    } catch (err: any) {
       console.error('Error calling generate-posts API:', err);
       suggestionsError.value = err.data?.message || err.message || 'Failed to generate suggestions.';
    }
    
    isLoadingSuggestions.value = false;
}

const findBestPostingTimes = async () => {
    if (!analysisResult.value?.suggestedSubreddits) return;

    timesError.value = null; // Reset specific error for this step

    console.log("Requesting best times for:", analysisResult.value.suggestedSubreddits);

    try {
        const response = await $fetch<BestTimesData>('/api/best-posting-times', {
            method: 'POST',
            body: {
                subreddits: analysisResult.value.suggestedSubreddits
            }
        });
        bestTimesData.value = response;
    } catch (err: any) {
        console.error('Error calling best-posting-times API:', err);
        // Set the specific time error, don't stop the main loading state
        timesError.value = err.data?.message || err.message || 'Failed to analyze posting times.';
    }
}

// Helper functions for formatting display
const formatDay = (dayIndex: number): string => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return days[dayIndex] || 'Invalid Day';
}
const formatHour = (hourUTC: number): string => {
    if (hourUTC < 0 || hourUTC > 23) return 'Invalid Hour';
    const hour12 = hourUTC % 12 === 0 ? 12 : hourUTC % 12;
    const ampm = hourUTC < 12 ? 'AM' : 'PM';
    return `${hour12}${ampm} UTC`; 
}

// Updated function to format time to local timezone
const formatTimeToLocal = (dayUTC: number, hourUTC: number): string => {
    if (typeof dayUTC !== 'number' || typeof hourUTC !== 'number' || dayUTC < 0 || dayUTC > 6 || hourUTC < 0 || hourUTC > 23) {
        return 'Invalid Time';
    }
    if (!localTimeZone.value) {
        return `(Waiting for timezone...) ${formatDay(dayUTC)} ${hourUTC}:00 UTC`; // Fallback before timezone is detected
    }

    try {
        // Create a reference date (e.g., start of this week in UTC)
        const now = new Date();
        const todayUtcDay = now.getUTCDay();
        const diff = dayUTC - todayUtcDay;
        const targetUtcDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + diff, hourUTC, 0, 0));

        // Format using Intl.DateTimeFormat for locale-aware output
        const formatter = new Intl.DateTimeFormat(undefined, { // Use browser's default locale
            timeZone: localTimeZone.value,
            weekday: 'short', 
            hour: 'numeric', 
            // minute: 'numeric', // Optional: add minutes if needed
            hour12: true, // Use AM/PM
        });
        
        return formatter.format(targetUtcDate);
    } catch (e) {
        console.error("Error formatting date:", e);
        // Fallback to UTC display on error
        const hour12 = hourUTC % 12 === 0 ? 12 : hourUTC % 12;
        const ampm = hourUTC < 12 ? 'AM' : 'PM';
        return `${formatDay(dayUTC)} ${hour12}${ampm} UTC (Format Error)`;
    }
}

// Allow editing suggestions in the textareas
const updateSuggestionTitle = (subreddit: string, newTitle: string) => {
    if (postSuggestions.value && postSuggestions.value[subreddit] && !('error' in postSuggestions.value[subreddit])) {
        (postSuggestions.value[subreddit] as PostSuggestion).title = newTitle;
    }
}
const updateSuggestionBody = (subreddit: string, newBody: string) => {
    if (postSuggestions.value && postSuggestions.value[subreddit] && !('error' in postSuggestions.value[subreddit])) {
        (postSuggestions.value[subreddit] as PostSuggestion).body = newBody;
    }
}

// Removed submitPost function

</script>

<style>
/* Add styles for the details/summary arrow if desired */
summary::marker {
  /* content: '' /* Or style the default marker */
  /* display: none; /* If using custom indicator */
}
/* Example: Custom arrow indicator */
/* summary::after { ... } */
</style> 