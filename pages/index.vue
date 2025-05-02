<template>
  <div class="min-h-screen bg-gray-100 py-10 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto bg-white p-6 sm:p-8 rounded-lg shadow-lg">
      <h1 class="text-3xl font-bold mb-8 text-center text-gray-800">Reddit Outreach Automator</h1>

      <!-- Top Section: Input & Analysis -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <!-- Left: URL Input -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">1. Analyze Article</h2>
          <form @submit.prevent="processArticle">
            <div class="mb-4">
              <label for="substack-url" class="block text-sm font-medium text-gray-700 mb-1">Substack Article URL</label>
              <input
                type="url"
                id="substack-url"
                v-model="articleUrl"
                placeholder="https://your-substack.com/p/your-article"
                required
                :disabled="isLoadingAnalysis"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
              />
            </div>
            <button
              type="submit"
              :disabled="isLoadingAnalysis"
              class="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center justify-center transition duration-150 ease-in-out"
            >
               <span v-if="!isLoadingAnalysis">Analyze Article, Rules & Best Times</span>
              <span v-else class="flex items-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                {{ loadingMessage }} 
              </span>
            </button>
             <!-- Analysis Loading Text (Dynamic) -->
             <div v-if="isLoadingAnalysis" class="text-center pt-4 text-sm text-gray-500">
                 {{ loadingMessage }}
             </div>
             <!-- Analysis Error Display -->
             <div v-if="analysisError && !isLoadingAnalysis" class="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
                <p class="font-medium">Analysis Error:</p>
                <p>{{ analysisError }}</p>
             </div>
             <!-- Analysis Time Warning Display -->
              <div v-if="timesError && !isLoadingAnalysis" class="mt-4 p-3 bg-orange-50 border border-orange-200 text-orange-700 rounded text-sm">
                <p class="font-medium">Time Analysis Warning:</p>
                <p>{{ timesError }}</p> 
             </div>
          </form>
        </div>

        <!-- Right: Analysis Results -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">Analysis Results</h2>
           <div v-if="!analysisResult && !isLoadingAnalysis" class="text-sm text-gray-500 italic">
              Analysis results (themes and keywords) will appear here after submitting a URL.
           </div>
           <div v-if="analysisResult" class="space-y-3">
            <div v-if="analysisResult.themes?.length">
                <h3 class="font-medium text-gray-600">Themes:</h3>
                <ul class="list-disc list-inside ml-4 text-sm text-gray-700">
                <li v-for="theme in analysisResult.themes" :key="`theme-${theme}`">{{ theme }}</li>
                </ul>
            </div>
            <div v-if="analysisResult.keywords?.length">
                <h3 class="font-medium text-gray-600">Keywords:</h3>
                <ul class="list-disc list-inside ml-4 text-sm text-gray-700">
                <li v-for="keyword in analysisResult.keywords" :key="`keyword-${keyword}`">{{ keyword }}</li>
                </ul>
            </div>
           </div>
        </div>
      </div>

       <!-- Middle Section: Combined Subreddits, Rules & Times -->
      <div v-if="analysisResult && analysisResult.suggestedSubreddits?.length" class="mb-8 border border-gray-200 rounded-lg p-6">
            <h2 class="text-xl font-semibold mb-4 text-gray-700">2. Suggested Subreddits, Rules & Best Times</h2>
            
            <!-- Loading/Error states for Times Analysis -->
            <div v-if="isLoadingAnalysis && analysisResult && !bestTimesData && !timesError" class="text-sm text-gray-500 italic mb-4">
                Analyzing best times...
            </div>
            <div v-if="timesError && !isLoadingAnalysis" class="p-3 bg-orange-50 border border-orange-200 text-orange-700 rounded text-sm mb-4">
                <p class="font-medium">Time Analysis Warning:</p>
                <p>{{ timesError }}</p> 
            </div>
            
            <!-- Combined List -->
            <ul class="space-y-4">
              <li v-for="subreddit in analysisResult.suggestedSubreddits" :key="`sub-${subreddit}`" class="bg-gray-50 rounded border border-gray-100">
                <details class="group">
                    <summary class="p-3 cursor-pointer list-none flex justify-between items-center">
                        <!-- Left side: Subreddit name and top time -->
                        <div class="flex items-center gap-x-4">
                           <span class="font-medium text-gray-800">{{ subreddit }}</span>
                           <!-- Display Top Time Here -->
                            <span v-if="bestTimesData && bestTimesData[subreddit]?.bestTimes?.length" class="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                                Best: {{ formatTimeToLocal(bestTimesData[subreddit]!.bestTimes![0].day, bestTimesData[subreddit]!.bestTimes![0].hour) }}
                            </span>
                            <span v-else-if="bestTimesData && bestTimesData[subreddit] && !bestTimesData[subreddit].error" class="text-xs text-gray-400 italic">
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