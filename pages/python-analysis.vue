<template>
  <div class="min-h-screen bg-gray-100 py-10 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto bg-white p-6 sm:p-8 rounded-lg shadow-lg">
      <h1 class="text-3xl font-bold mb-8 text-center text-gray-800">Python Analysis Tool</h1>
      <p class="text-center text-gray-600 mb-8">Advanced Reddit analysis with cost optimization, sentiment analysis, and comprehensive insights</p>

      <!-- Main Content -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Left: Configuration Panel -->
        <div class="border border-gray-200 rounded-lg p-6">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">1. Configure Analysis</h2>
          
          <!-- Harvest Mode Selection -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-2">Harvest Mode</label>
            <div class="grid grid-cols-3 gap-3">
              <button 
                v-for="mode in ['smart', 'delta', 'full']" 
                :key="mode"
                @click="harvestMode = mode"
                :class="[
                  'py-2 px-4 border rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500',
                  harvestMode === mode 
                    ? 'bg-indigo-600 text-white border-indigo-600' 
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                ]"
              >
                {{ mode.charAt(0).toUpperCase() + mode.slice(1) }}
              </button>
            </div>
            <p class="mt-1 text-xs text-gray-500">
              <span v-if="harvestMode === 'smart'">Auto delta (Recommended)</span>
              <span v-else-if="harvestMode === 'delta'">Fast updates only</span>
              <span v-else>Complete scan</span>
            </p>
          </div>
          
          <!-- Subreddit Selection -->
          <div class="mb-6">
            <label for="subreddit-select" class="block text-sm font-medium text-gray-700 mb-2">Subreddits</label>
            
            <!-- NZ Subreddits Dropdown -->
            <div class="flex mb-2">
              <select
                id="subreddit-select"
                v-model="selectedSubredditOption"
                @change="addFromDropdown"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-l-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select a NZ subreddit...</option>
                <optgroup v-for="category in groupedSubreddits" :key="category.name" :label="category.name">
                  <option v-for="sub in category.subreddits" :key="sub.name" :value="sub.name">
                    r/{{ sub.name }} ({{ formatSubscribers(sub.subscribers) }}) - {{ sub.description }}
                  </option>
                </optgroup>
              </select>
              <button
                @click="addFromDropdown"
                class="bg-indigo-600 px-4 py-2 border border-l-0 border-indigo-600 rounded-r-md text-white hover:bg-indigo-700 focus:outline-none"
              >
                Add
              </button>
            </div>
            
            <!-- Manual Input -->
            <div class="flex mb-2">
              <input
                id="subreddit-input"
                v-model="subredditInput"
                @keyup.enter="addSubreddit"
                type="text"
                placeholder="Or enter custom subreddit name"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-l-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
              <button
                @click="addSubreddit"
                class="bg-gray-200 px-4 py-2 border border-l-0 border-gray-300 rounded-r-md text-gray-700 hover:bg-gray-300 focus:outline-none"
              >
                Add
              </button>
            </div>
            
            <!-- Selected Subreddits -->
            <div class="border border-gray-200 rounded-md p-3 min-h-[80px]">
              <div v-if="selectedSubreddits.length === 0" class="text-gray-400 italic text-sm">
                No subreddits selected
              </div>
              <div v-else class="flex flex-wrap gap-2">
                <div 
                  v-for="(sub, index) in selectedSubreddits" 
                  :key="index"
                  class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded-md text-sm flex items-center"
                >
                  r/{{ sub }}
                  <button 
                    @click="removeSubreddit(index)" 
                    class="ml-1 text-indigo-600 hover:text-indigo-800 focus:outline-none"
                  >
                    &times;
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Preset Groups -->
            <div class="mt-3">
              <label class="block text-sm font-medium text-gray-700 mb-2">Preset Groups</label>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <button
                  v-for="group in ['finance', 'tech', 'business', 'productivity']"
                  :key="group"
                  @click="addPresetGroup(group)"
                  class="bg-gray-100 border border-gray-300 rounded-md py-1 px-2 text-sm text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {{ group }}
                </button>
              </div>
            </div>
          </div>
          
          <!-- Options -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-2">Options</label>
            
            <div class="mb-3">
              <label for="posts-per-sub" class="block text-sm text-gray-600 mb-1">Posts per Subreddit</label>
              <select
                id="posts-per-sub"
                v-model="postsPerSub"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Auto (Smart: 200 delta, 500 full)</option>
                <option value="50">50 - Quick test</option>
                <option value="100">100 - Light harvest</option>
                <option value="200">200 - Standard</option>
                <option value="500">500 - Heavy harvest</option>
                <option value="1000">1000 - Maximum</option>
              </select>
            </div>
            
            <div class="mb-3">
              <label for="output-name" class="block text-sm text-gray-600 mb-1">Output Name (optional)</label>
              <input
                id="output-name"
                v-model="outputName"
                type="text"
                placeholder="custom_harvest_name"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            
            <div class="flex items-center">
              <input
                id="no-database"
                v-model="noDatabase"
                type="checkbox"
                class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label for="no-database" class="ml-2 block text-sm text-gray-600">
                JSON-only mode (no database)
              </label>
            </div>
            <div v-if="noDatabase" class="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-700">
              ⚠️ JSON-only mode disables fast delta updates
            </div>
          </div>
          
          <!-- Action Buttons -->
          <div>
            <button
              @click="startHarvest"
              :disabled="isLoading || selectedSubreddits.length === 0"
              class="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center justify-center mb-3"
            >
              <span v-if="!isLoading">🚀 Start Harvest</span>
              <span v-else class="flex items-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            </button>
            <button
              @click="runAnalysis"
              :disabled="isAnalyzing || selectedSubreddits.length === 0"
              class="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 flex items-center justify-center mb-3"
            >
              <span v-if="!isAnalyzing">🔍 Analyze Data</span>
              <span v-else class="flex items-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
              </span>
            </button>
            <button
              @click="refreshStats"
              class="w-full bg-gray-200 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            >
              📊 Refresh Stats
            </button>
          </div>
        </div>
        
        <!-- Right: Status Panel -->
        <div class="border border-gray-200 rounded-lg p-6 bg-gray-50">
          <h2 class="text-xl font-semibold mb-4 text-gray-700">2. Status & Results</h2>
          
          <!-- Database Stats -->
          <div class="mb-6">
            <h3 class="text-lg font-medium mb-3 text-gray-700">Database Stats</h3>
            <div class="grid grid-cols-3 gap-4">
              <div class="bg-white p-4 rounded-lg shadow-sm text-center">
                <div class="text-2xl font-bold text-indigo-600">{{ stats.totalPosts || '-' }}</div>
                <div class="text-sm text-gray-500">Posts</div>
              </div>
              <div class="bg-white p-4 rounded-lg shadow-sm text-center">
                <div class="text-2xl font-bold text-indigo-600">{{ stats.totalComments || '-' }}</div>
                <div class="text-sm text-gray-500">Comments</div>
              </div>
              <div class="bg-white p-4 rounded-lg shadow-sm text-center">
                <div class="text-2xl font-bold text-indigo-600">{{ stats.totalSubreddits || '-' }}</div>
                <div class="text-sm text-gray-500">Subreddits</div>
              </div>
            </div>
          </div>
          
          <!-- Harvest Status -->
          <div class="mb-6">
            <h3 class="text-lg font-medium mb-3 text-gray-700">Harvest Status</h3>
            <div 
              class="p-4 rounded-lg border-l-4"
              :class="{
                'bg-blue-50 border-blue-500': !isLoading && !harvestError,
                'bg-yellow-50 border-yellow-500': isLoading,
                'bg-red-50 border-red-500': harvestError
              }"
            >
              <div class="font-medium" :class="{
                'text-blue-700': !isLoading && !harvestError,
                'text-yellow-700': isLoading,
                'text-red-700': harvestError
              }">
                {{ statusMessage }}
              </div>
              <div v-if="isLoading" class="w-full h-2 bg-gray-200 rounded-full mt-2 overflow-hidden">
                <div class="h-full bg-indigo-600 rounded-full animate-pulse" style="width: 100%"></div>
              </div>
            </div>
            
            <!-- Command Output -->
            <div v-if="commandOutput" class="mt-4">
              <div class="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm overflow-auto max-h-[200px]">
                <pre>{{ commandOutput }}</pre>
              </div>
            </div>
          </div>
          
          <!-- Tools -->
          <div>
            <h3 class="text-lg font-medium mb-3 text-gray-700">Tools</h3>
            <div class="grid grid-cols-2 gap-3">
              <button
                @click="showResetModal = true"
                class="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Reset Checkpoint
              </button>
              <button
                @click="downloadData"
                class="bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Download Data
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Analysis Results Section -->
      <div v-if="analysisResults" class="mt-8 border-t border-gray-200 pt-8">
        <h2 class="text-2xl font-bold mb-6 text-center text-gray-800">Analysis Results</h2>
        
        <!-- Analysis Summary -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <!-- Cost Optimization -->
          <div class="border border-gray-200 rounded-lg p-6 bg-blue-50">
            <h3 class="text-lg font-semibold mb-3 text-blue-700">💰 Cost Optimization</h3>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">API Calls Made:</span>
                <span class="font-medium">{{ analysisResults?.api_usage?.api_calls_made || 0 }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">API Calls Saved:</span>
                <span class="font-medium text-green-600">{{ analysisResults?.api_usage?.api_calls_saved || 0 }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Estimated Cost:</span>
                <span class="font-medium">${{ (analysisResults?.api_usage?.estimated_cost || 0).toFixed(4) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Savings:</span>
                <span class="font-medium text-green-600">${{ (analysisResults?.api_usage?.estimated_savings || 0).toFixed(4) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Efficiency:</span>
                <span class="font-medium text-blue-600">{{ ((analysisResults?.api_usage?.efficiency_ratio || 0) * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          
          <!-- Analysis Stats -->
          <div class="border border-gray-200 rounded-lg p-6 bg-purple-50">
            <h3 class="text-lg font-semibold mb-3 text-purple-700">📊 Analysis Stats</h3>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Clusters Processed:</span>
                <span class="font-medium">{{ analysisResults?.api_usage?.total_clusters_processed || 0 }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Opportunities Found:</span>
                <span class="font-medium">{{ analysisResults?.opportunities?.length || 0 }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Runtime:</span>
                <span class="font-medium">{{ (analysisResults?.analysis_metadata?.total_runtime || 0).toFixed(2) }}s</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-gray-600">Timestamp:</span>
                <span class="font-medium text-xs">{{ analysisResults?.analysis_metadata?.timestamp || 'N/A' }}</span>
              </div>
            </div>
          </div>
          
          <!-- Quick Actions -->
          <div class="border border-gray-200 rounded-lg p-6 bg-gray-50">
            <h3 class="text-lg font-semibold mb-3 text-gray-700">⚡ Quick Actions</h3>
            <div class="space-y-2">
              <button 
                @click="runAnalysis"
                :disabled="isAnalyzing"
                class="w-full bg-green-600 text-white py-2 px-3 rounded-md hover:bg-green-700 focus:outline-none text-sm"
              >
                🔄 Re-analyze
              </button>
              <button 
                @click="refreshStats"
                class="w-full bg-gray-600 text-white py-2 px-3 rounded-md hover:bg-gray-700 focus:outline-none text-sm"
              >
                📈 Refresh Stats
              </button>
              <button 
                @click="downloadData"
                class="w-full bg-blue-600 text-white py-2 px-3 rounded-md hover:bg-blue-700 focus:outline-none text-sm"
              >
                💾 Download Data
              </button>
            </div>
          </div>
        </div>
        
        <!-- Opportunities Details -->
        <div class="grid grid-cols-1 gap-6">
          <div class="border border-gray-200 rounded-lg p-6">
            <h3 class="text-xl font-semibold mb-4 text-green-700">💡 Discovered Opportunities</h3>
            <div v-if="analysisResults?.opportunities?.length" class="space-y-4">
              <div v-for="(opportunity, index) in analysisResults.opportunities" :key="index" 
                   class="bg-green-50 border border-green-200 rounded-lg p-4">
                                 <div class="flex justify-between items-start mb-3">
                   <h4 class="font-semibold text-green-800">{{ opportunity.problem_summary || 'Unknown Problem' }}</h4>
                   <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                     Score: {{ (opportunity.opportunity_score || 0).toFixed(1) }}
                   </span>
                 </div>
                 
                 <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                   <div>
                     <span class="text-xs text-gray-500">Cluster Size</span>
                     <div class="font-medium">{{ opportunity.cluster_size || 0 }} problems</div>
                   </div>
                   <div>
                     <span class="text-xs text-gray-500">Avg Score</span>
                     <div class="font-medium">{{ (opportunity.avg_score || 0).toFixed(1) }}</div>
                   </div>
                   <div>
                     <span class="text-xs text-gray-500">Sentiment</span>
                     <div class="font-medium">{{ (opportunity.avg_sentiment || 0).toFixed(3) }}</div>
                   </div>
                   <div>
                     <span class="text-xs text-gray-500">Subreddits</span>
                     <div class="font-medium">{{ (opportunity.subreddits || []).join(', ') }}</div>
                   </div>
                 </div>
                
                <div v-if="opportunity.business_opportunity" class="mt-4 p-3 bg-green-100 rounded-lg">
                  <h5 class="font-medium text-green-800 mb-2">{{ opportunity.business_opportunity.title }}</h5>
                  <p class="text-green-700 text-sm mb-2">{{ opportunity.business_opportunity.description }}</p>
                  <div class="flex flex-wrap gap-1 mb-2">
                    <span v-for="keyword in opportunity.business_opportunity.keywords" :key="keyword" 
                          class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-200 text-green-800">
                      {{ keyword }}
                    </span>
                  </div>
                </div>
                
                <div v-else-if="opportunity.skipped_ai_analysis" class="mt-4 p-3 bg-yellow-100 rounded-lg">
                  <div class="flex items-center text-yellow-800">
                    <span class="text-sm">⚠️ {{ opportunity.skip_reason }}</span>
                  </div>
                </div>
                
                <!-- Post References Section -->
                <div v-if="opportunity.post_references && opportunity.post_references.length > 0" class="mt-4 p-3 bg-gray-50 rounded-lg">
                  <h6 class="font-medium text-gray-800 mb-2">📝 Original Posts & Comments</h6>
                  <div class="space-y-3">
                    <div v-for="(ref, refIndex) in opportunity.post_references.slice(0, 3)" :key="refIndex" 
                         class="border-l-4 border-blue-200 pl-3 bg-white p-2 rounded">
                      <div class="flex items-start justify-between mb-1">
                        <div class="flex items-center space-x-2">
                          <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                                :class="ref.type === 'post' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'">
                            {{ ref.type === 'post' ? '📄 Post' : '💬 Comment' }}
                          </span>
                          <span class="text-sm text-gray-600">r/{{ ref.subreddit }}</span>
                          <span class="text-sm text-gray-600">Score: {{ ref.score }}</span>
                        </div>
                        <a :href="ref.reddit_url" target="_blank" rel="noopener noreferrer" 
                           class="text-blue-600 hover:text-blue-800 text-sm">
                          View on Reddit ↗
                        </a>
                      </div>
                      <p class="text-sm text-gray-700 mb-2">{{ ref.text }}</p>
                      <div class="flex items-center space-x-4 text-xs text-gray-500">
                        <span>Confidence: {{ (ref.problem_confidence * 100).toFixed(1) }}%</span>
                        <span>Sentiment: {{ ref.sentiment?.polarity?.toFixed(2) || 'N/A' }}</span>
                        <span>Engagement: {{ ref.engagement || 0 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-gray-500 italic">No opportunities found. Try running analysis with more data or different subreddits.</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Reset Modal -->
    <div v-if="showResetModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 max-w-md w-full">
        <h3 class="text-lg font-medium mb-4">Reset Checkpoint</h3>
        <p class="mb-4 text-gray-600">Enter subreddit name to reset its harvest checkpoint:</p>
        <input 
          v-model="resetSubreddit" 
          type="text" 
          placeholder="e.g., PersonalFinanceNZ"
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 mb-4"
        />
        <div class="flex justify-end space-x-3">
          <button 
            @click="showResetModal = false"
            class="bg-gray-200 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button 
            @click="resetCheckpoint"
            class="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';

// Interface definitions
interface SubredditOption {
  name: string;
  subscribers: number;
  description: string;
  category: string;
  business_relevance: string;
}

interface GroupedSubreddits {
  name: string;
  subreddits: SubredditOption[];
}

interface AnalysisResults {
  opportunities: Array<{
    problem_summary: string;
    cluster_size: number;
    total_score: number;
    avg_score: number;
    subreddits: string[];
    skipped_ai_analysis?: boolean;
    skip_reason?: string;
    avg_sentiment: number;
    opportunity_score: number;
    business_opportunity?: {
      title: string;
      description: string;
      keywords: string[];
      market_size: string;
      pain_level: string;
      solution_difficulty: string;
      competition_level: string;
      business_model: string;
      next_steps: string[];
    };
    post_references?: Array<{
      text: string;
      type: string;
      score: number;
      subreddit: string;
      post_id: string;
      reddit_url: string;
      sentiment?: {
        polarity: number;
        subjectivity: number;
      };
      problem_confidence: number;
      engagement: number;
      comment_id?: string;
    }>;
  }>;
  api_usage: {
    api_calls_made: number;
    api_calls_saved: number;
    estimated_cost: number;
    estimated_savings: number;
    total_clusters_processed: number;
    efficiency_ratio: number;
  };
  analysis_metadata: {
    timestamp: string;
    total_runtime: number;
    config_used: any;
  };
}

// State variables
const harvestMode = ref('smart');
const subredditInput = ref('');
const selectedSubreddits = ref<string[]>([]);
const postsPerSub = ref('');
const outputName = ref('');
const noDatabase = ref(false);
const isLoading = ref(false);
const isAnalyzing = ref(false);
const statusMessage = ref('Ready to harvest');
const harvestError = ref('');
const commandOutput = ref('');
const showResetModal = ref(false);
const resetSubreddit = ref('');
const analysisResults = ref<AnalysisResults | null>(null);
const selectedSubredditOption = ref('');
const availableSubreddits = ref<SubredditOption[]>([]);

// Database stats
const stats = ref({
  totalPosts: 0,
  totalComments: 0,
  totalSubreddits: 0
});

// Preset groups mapping
const presetGroups: Record<string, string[]> = {
  finance: ['PersonalFinance', 'PersonalFinanceNZ', 'Fire', 'investing', 'financialindependence'],
  tech: ['programming', 'webdev', 'startups', 'entrepreneur', 'SaaS'],
  business: ['entrepreneur', 'startups', 'smallbusiness', 'marketing', 'sales'],
  productivity: ['productivity', 'getmotivated', 'organization', 'TimeManagement']
};

// Computed properties
const groupedSubreddits = computed<GroupedSubreddits[]>(() => {
  const groups: Record<string, SubredditOption[]> = {};
  
  availableSubreddits.value.forEach(sub => {
    if (!groups[sub.category]) {
      groups[sub.category] = [];
    }
    groups[sub.category].push(sub);
  });
  
  return Object.keys(groups).map(category => ({
    name: category,
    subreddits: groups[category]
  }));
});

// Utility methods
const formatSubscribers = (count: number): string => {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  } else if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
};

// Methods
const addSubreddit = () => {
  const subreddit = subredditInput.value.trim().replace(/^r\//, '');
  if (subreddit && !selectedSubreddits.value.includes(subreddit)) {
    selectedSubreddits.value.push(subreddit);
    subredditInput.value = '';
  }
};

const addFromDropdown = () => {
  const subreddit = selectedSubredditOption.value;
  if (subreddit && !selectedSubreddits.value.includes(subreddit)) {
    selectedSubreddits.value.push(subreddit);
    selectedSubredditOption.value = '';
  }
};

const removeSubreddit = (index: number) => {
  selectedSubreddits.value.splice(index, 1);
};

const addPresetGroup = (group: string) => {
  const subreddits = presetGroups[group] || [];
  for (const sub of subreddits) {
    if (!selectedSubreddits.value.includes(sub)) {
      selectedSubreddits.value.push(sub);
    }
  }
};

const refreshStats = async () => {
  try {
    const response = await fetch('/api/python-analysis/stats');
    const data = await response.json();
    
    if (data.success) {
      stats.value = data.stats;
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error);
  }
};

const startHarvest = async () => {
  if (selectedSubreddits.value.length === 0) {
    harvestError.value = 'Please select at least one subreddit';
    return;
  }
  
  isLoading.value = true;
  harvestError.value = '';
  statusMessage.value = 'Starting harvest...';
  commandOutput.value = '';
  
  try {
    const response = await fetch('/api/python-analysis/harvest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subreddits: selectedSubreddits.value,
        mode: harvestMode.value,
        posts_per_sub: postsPerSub.value ? parseInt(postsPerSub.value) : undefined,
        no_database: noDatabase.value,
        output_name: outputName.value || undefined
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      statusMessage.value = 'Harvest completed successfully!';
      commandOutput.value = data.output || 'No output available';
      
      // If analysis results are available
      if (data.results) {
        analysisResults.value = data.results;
      }
      
      // Refresh stats after successful harvest
      refreshStats();
    } else {
      harvestError.value = data.error || 'Unknown error occurred';
      statusMessage.value = 'Harvest failed!';
      commandOutput.value = data.output || '';
    }
  } catch (error: any) {
    harvestError.value = error.message || 'Failed to start harvest';
    statusMessage.value = 'Error occurred!';
  } finally {
    isLoading.value = false;
  }
};

const resetCheckpoint = async () => {
  if (!resetSubreddit.value.trim()) {
    return;
  }
  
  try {
    const response = await fetch('/api/python-analysis/reset-checkpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subreddit: resetSubreddit.value.trim()
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      statusMessage.value = `Reset checkpoint for r/${resetSubreddit.value}`;
      showResetModal.value = false;
      resetSubreddit.value = '';
      refreshStats();
    } else {
      harvestError.value = data.error || 'Failed to reset checkpoint';
    }
  } catch (error: any) {
    harvestError.value = error.message || 'Error resetting checkpoint';
  }
};

const runAnalysis = async () => {
  if (selectedSubreddits.value.length === 0) {
    harvestError.value = 'Please select at least one subreddit';
    return;
  }
  
  isAnalyzing.value = true;
  harvestError.value = '';
  statusMessage.value = 'Starting analysis...';
  
  try {
    const response = await fetch('/api/python-analysis/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subreddits: selectedSubreddits.value,
        mode: 'basic', // Start with basic analysis for faster results
        max_problems: 50
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      statusMessage.value = 'Analysis completed successfully!';
      commandOutput.value = data.output || 'No output available';
      
      // Use the structured JSON results from the API
      if (data.results) {
        analysisResults.value = data.results;
      } else {
        analysisResults.value = {
          opportunities: [],
          api_usage: {
            api_calls_made: 0,
            api_calls_saved: 0,
            estimated_cost: 0,
            estimated_savings: 0,
            total_clusters_processed: 0,
            efficiency_ratio: 0
          },
          analysis_metadata: {
            timestamp: new Date().toISOString(),
            total_runtime: 0,
            config_used: {}
          }
        };
      }
    } else {
      harvestError.value = data.error || 'Analysis failed';
      statusMessage.value = 'Analysis failed!';
      commandOutput.value = data.output || '';
    }
  } catch (error: any) {
    harvestError.value = error.message || 'Failed to run analysis';
    statusMessage.value = 'Error occurred!';
  } finally {
    isAnalyzing.value = false;
  }
};

const loadSubreddits = async () => {
  try {
    const response = await fetch('/api/subreddits-nz');
    const data = await response.json();
    
    if (data.success) {
      availableSubreddits.value = data.subreddits;
    }
  } catch (error) {
    console.error('Failed to load subreddits:', error);
  }
};

const downloadData = () => {
  // This would be implemented to download data
  alert('Data download feature coming soon!');
};

// Initialize
onMounted(() => {
  refreshStats();
  loadSubreddits();
});
</script>