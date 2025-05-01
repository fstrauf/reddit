<template>
  <div class="min-h-screen bg-gray-100 flex items-center justify-center py-12">
    <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-2xl">
      <h1 class="text-2xl font-bold mb-6 text-center">Reddit Outreach Automator</h1>
      
      <!-- URL Input Form -->
      <form @submit.prevent="processArticle" class="mb-8">
        <div class="mb-4">
          <label for="substack-url" class="block text-sm font-medium text-gray-700 mb-2">Substack Article URL</label>
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
          class="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center justify-center"
        >
           <span v-if="!isLoadingAnalysis">Analyze Article</span>
          <span v-else>
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            Analyzing...
          </span>
        </button>
      </form>

      <!-- Loading Indicator for Analysis -->
       <div v-if="isLoadingAnalysis" class="text-center py-6">
         <p class="text-gray-600 flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            Analyzing article and fetching subreddit rules...
         </p>
       </div>

      <!-- Analysis Error Display -->
      <div v-if="analysisError && !isLoadingAnalysis" class="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
        <p class="font-bold">Analysis Error:</p>
        <p>{{ analysisError }}</p>
      </div>

      <!-- Results Area -->
      <div v-if="analysisResult && !isLoadingAnalysis" class="space-y-6">
        <!-- Analysis Results -->
        <div class="p-4 border border-gray-200 rounded">
          <h2 class="text-lg font-semibold mb-2">Article Analysis:</h2>
          <div v-if="analysisResult.themes?.length">
            <h3 class="font-medium">Themes:</h3>
            <ul class="list-disc list-inside ml-4 text-sm text-gray-700">
              <li v-for="theme in analysisResult.themes" :key="`theme-${theme}`">{{ theme }}</li>
            </ul>
          </div>
          <div v-if="analysisResult.keywords?.length" class="mt-2">
            <h3 class="font-medium">Keywords:</h3>
            <ul class="list-disc list-inside ml-4 text-sm text-gray-700">
              <li v-for="keyword in analysisResult.keywords" :key="`keyword-${keyword}`">{{ keyword }}</li>
            </ul>
          </div>
        </div>

        <!-- Suggested Subreddits & Rules -->
        <div v-if="analysisResult.suggestedSubreddits?.length" class="p-4 border border-gray-200 rounded">
          <h2 class="text-lg font-semibold mb-2">Suggested Subreddits & Rules:</h2>
          <ul class="space-y-4">
            <li v-for="subreddit in analysisResult.suggestedSubreddits" :key="`sub-${subreddit}`" class="p-3 bg-gray-50 rounded border border-gray-100">
              <div class="flex justify-between items-center mb-2">
                <span class="font-medium">{{ subreddit }}</span>
              </div>
              
              <!-- Rules Display Area -->
               <div v-if="rulesData && rulesData[subreddit] && 'error' in rulesData[subreddit]" class="mt-2 p-2 text-xs bg-red-100 border border-red-300 text-red-700 rounded">
                <p class="font-bold">Error fetching rules:</p>
                <p>{{ rulesData[subreddit].error }}</p>
              </div>
              <div v-else-if="rulesData && rulesData[subreddit]" class="mt-2 text-xs space-y-1 text-gray-600">
                  <h4 class="font-semibold">Rules:</h4>
                  <ul v-if="(rulesData[subreddit] as SubredditRule[]).length > 0" class="list-decimal list-inside space-y-1">
                      <li v-for="(rule, index) in (rulesData[subreddit] as SubredditRule[])" :key="index">
                          <strong class="font-medium">{{ rule.short_name }}</strong>
                          <p v-if="rule.description" class="ml-4 text-gray-500">{{ rule.description }}</p>
                      </li>
                  </ul>
                  <p v-else class="text-gray-500 italic">No rules listed via API.</p>
              </div>
               <div v-else class="mt-2 text-xs text-gray-400 italic">
                 (Rules could not be determined)
              </div>
            </li>
          </ul>
          
          <!-- Button to Generate Posts -->
           <div class="mt-6 text-center">
               <button 
                  @click="generatePostSuggestions"
                  :disabled="isLoadingSuggestions || !analysisResult || !rulesData" 
                  class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50 flex items-center justify-center mx-auto"
                >
                   <span v-if="!isLoadingSuggestions">Generate Post Suggestions</span>
                   <span v-else>
                      <svg class="animate-spin h-5 w-5 text-white mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      Generating...
                   </span>
               </button>
           </div>
        </div>
        
        <!-- Area for Post Suggestions (to be added) -->
        <div v-if="postSuggestions">
            <!-- Display generated suggestions here -->
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// Interfaces
interface AnalysisResultData {
  themes: string[];
  keywords: string[];
  suggestedSubreddits: string[];
}
interface SubredditRule {
    short_name: string;
    description: string;
    kind: string; // e.g., "all", "link", "comment"
    // Add other potential fields if needed
}
// Type for the rules part of the response (mapping sub name to rules or error)
type RulesData = Record<string, SubredditRule[] | { error: string }>;
// Type for the combined response from the analyze API
interface CombinedAnalysisResponse {
    analysis: AnalysisResultData;
    rules: RulesData;
}
// Placeholder for post suggestions structure
interface PostSuggestion {
    title: string;
    body: string;
}

// Reactive State
const articleUrl = ref('')
const isLoadingAnalysis = ref(false)
const analysisResult = ref<AnalysisResultData | null>(null)
const rulesData = ref<RulesData | null>(null) // Store the whole rules dictionary
const analysisError = ref<string | null>(null)
const isLoadingSuggestions = ref(false)
const postSuggestions = ref<Record<string, PostSuggestion | {error: string}> | null>(null) // Placeholder
const suggestionsError = ref<string | null>(null) // Placeholder

// Methods
const processArticle = async () => {
  if (!articleUrl.value) return;

  isLoadingAnalysis.value = true
  analysisResult.value = null
  rulesData.value = null // Clear rules
  analysisError.value = null
  postSuggestions.value = null // Clear suggestions
  suggestionsError.value = null // Clear suggestions error

  try {
    // Fetch combined analysis and rules
    const response = await $fetch<CombinedAnalysisResponse>('/api/analyze-article', {
      method: 'POST',
      body: { url: articleUrl.value },
    })
    analysisResult.value = response.analysis
    rulesData.value = response.rules
  } catch (err: any) {
    console.error('Error calling analyze API:', err)
    analysisError.value = err.data?.message || err.message || 'An unknown error occurred.'
  } finally {
    isLoadingAnalysis.value = false
  }
}

// Placeholder for generating suggestions
const generatePostSuggestions = async () => {
    if (!analysisResult.value || !rulesData.value) return;

    isLoadingSuggestions.value = true;
    postSuggestions.value = null;
    suggestionsError.value = null;

    console.log("Data for suggestions:", {
        analysis: analysisResult.value,
        rules: rulesData.value
        // We also need the original article text here!
        // Need to pass articleUrl or fetched text to the backend
    });

    // --- TODO: Implement API call to /api/generate-posts --- 
    // Pass necessary data: article content/url, analysis, rules
    // try {
    //    const response = await $fetch('/api/generate-posts', { ... });
    //    postSuggestions.value = response.suggestions;
    // } catch (err) {
    //    suggestionsError.value = ... 
    // }

    // Simulate loading for now
    await new Promise(resolve => setTimeout(resolve, 1500)); 
    suggestionsError.value = "Suggestion generation not implemented yet.";
    
    isLoadingSuggestions.value = false;
}

</script> 