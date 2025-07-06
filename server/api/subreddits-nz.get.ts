import { readFileSync } from 'fs';
import path from 'path';

interface SubredditOption {
  name: string;
  subscribers: number;
  description: string;
  category: string;
  business_relevance: string;
}

export default defineEventHandler(async (event) => {
  try {
    // Read the subreddits JSON file from the Python analysis directory
    const pythonAnalysisPath = path.join(process.cwd(), '..', 'python_analysis_reddit');
    const subredditsFilePath = path.join(pythonAnalysisPath, 'subreddits_nz.json');
    
    const fileContent = readFileSync(subredditsFilePath, 'utf-8');
    const data = JSON.parse(fileContent);
    
    const subreddits: SubredditOption[] = [];
    
    // Extract subreddits from different tiers and categories
    const nzSubreddits = data.nz_subreddits;
    
    // Add tier 1 major subreddits
    if (nzSubreddits.tiers?.tier_1_major?.subreddits) {
      nzSubreddits.tiers.tier_1_major.subreddits.forEach((sub: any) => {
        subreddits.push({
          name: sub.name,
          subscribers: sub.subscribers,
          description: sub.description,
          category: `Tier 1 - ${sub.category}`,
          business_relevance: sub.business_relevance
        });
      });
    }
    
    // Add tier 2 medium subreddits
    if (nzSubreddits.tiers?.tier_2_medium?.subreddits) {
      nzSubreddits.tiers.tier_2_medium.subreddits.forEach((sub: any) => {
        subreddits.push({
          name: sub.name,
          subscribers: sub.subscribers,
          description: sub.description,
          category: `Tier 2 - ${sub.category}`,
          business_relevance: sub.business_relevance
        });
      });
    }
    
    // Add business/finance subreddits
    if (nzSubreddits.categories?.business_finance) {
      nzSubreddits.categories.business_finance.forEach((sub: any) => {
        // Only add if not already included
        if (!subreddits.find(s => s.name === sub.name)) {
          subreddits.push({
            name: sub.name,
            subscribers: sub.subscribers,
            description: sub.description,
            category: 'Business & Finance',
            business_relevance: sub.business_relevance
          });
        }
      });
    }
    
    // Add major regional subreddits
    if (nzSubreddits.categories?.regional_cities) {
      nzSubreddits.categories.regional_cities.forEach((sub: any) => {
        // Only add if not already included and has reasonable size
        if (!subreddits.find(s => s.name === sub.name) && sub.subscribers > 5000) {
          subreddits.push({
            name: sub.name,
            subscribers: sub.subscribers,
            description: sub.description,
            category: 'Regional Cities',
            business_relevance: sub.business_relevance
          });
        }
      });
    }
    
    // Sort by business relevance and then by subscribers
    const relevanceOrder = { 'very_high': 4, 'high': 3, 'medium': 2, 'low': 1 };
    subreddits.sort((a, b) => {
      const aRelevance = relevanceOrder[a.business_relevance as keyof typeof relevanceOrder] || 0;
      const bRelevance = relevanceOrder[b.business_relevance as keyof typeof relevanceOrder] || 0;
      
      if (aRelevance !== bRelevance) {
        return bRelevance - aRelevance; // Higher relevance first
      }
      
      return b.subscribers - a.subscribers; // Then by subscriber count
    });
    
    return {
      success: true,
      subreddits: subreddits,
      total: subreddits.length
    };
    
  } catch (error: any) {
    console.error('Error loading NZ subreddits:', error);
    
    return {
      success: false,
      error: error.message || 'Failed to load subreddits',
      subreddits: []
    };
  }
}); 