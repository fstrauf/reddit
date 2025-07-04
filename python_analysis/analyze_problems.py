#!/usr/bin/env python3
"""
Smart AI Problem Analyzer - Uses embeddings to cluster similar problems first
Then analyzes representative samples with GPT-4 for business opportunities
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env.local')

class SmartProblemAnalyzer:
    """Smart problem analyzer using embeddings and clustering"""
    
    def __init__(self):
        # Setup OpenAI
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = openai.OpenAI(api_key=self.openai_key)
        
        # Setup embedding model (lightweight, fast)
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.data = []
        
    def load_harvest_data(self, filename: str = 'output/latest_harvest.json') -> None:
        """Load harvested Reddit data"""
        print(f"📂 Loading harvested data from {filename}...")
        
        try:
            with open(filename, 'r') as f:
                self.data = json.load(f)
            
            total_posts = len(self.data)
            total_comments = sum(len(post['comments']) for post in self.data)
            print(f"✅ Loaded {total_posts:,} posts with {total_comments:,} comments")
            
        except FileNotFoundError:
            print(f"❌ File {filename} not found. Run harvest_reddit.py first!")
            return
    
    def extract_problem_texts(self) -> List[Dict]:
        """Extract problem-related texts with metadata"""
        print(f"🔍 Extracting problem statements...")
        
        # Problem indicators
        problem_indicators = [
            'problem', 'issue', 'struggle', 'difficult', 'hard', 'annoying', 'frustrating',
            'hate', 'terrible', 'awful', 'sucks', 'broken', 'doesnt work', "doesn't work",
            'bug', 'error', 'fail', 'crash', 'slow', 'expensive', 'waste', 'time consuming',
            'wish there was', 'need a solution', 'looking for', 'help with', 'stuck with',
            'cant find', 'no way to', 'impossible', 'ridiculous', 'pain', 'nightmare'
        ]
        
        problem_texts = []
        
        for post in self.data:
            # Check post title and selftext
            post_text = f"{post['title']} {post['selftext']}".strip()
            if len(post_text) > 50 and any(indicator in post_text.lower() for indicator in problem_indicators):
                problem_texts.append({
                    'text': post_text,
                    'type': 'post',
                    'score': post['score'],
                    'subreddit': post['subreddit'],
                    'post_id': post['id'],
                    'upvote_ratio': post.get('upvote_ratio', 0.5)
                })
            
            # Check comments (limit to avoid too much data)
            for comment in post['comments']:
                if (len(comment['text']) > 30 and 
                    comment['score'] > 0 and  # Only positive score comments
                    any(indicator in comment['text'].lower() for indicator in problem_indicators)):
                    
                    problem_texts.append({
                        'text': comment['text'],
                        'type': 'comment', 
                        'score': comment['score'],
                        'subreddit': post['subreddit'],
                        'post_id': post['id'],
                        'comment_id': comment['id']
                    })
        
        # Sort by score to prioritize higher-rated problems
        problem_texts.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"🎯 Found {len(problem_texts)} problem statements")
        return problem_texts
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for texts"""
        print(f"🔢 Creating embeddings for {len(texts)} texts...")
        
        # Truncate texts to avoid memory issues
        truncated_texts = [text[:500] for text in texts]
        
        embeddings = self.embedding_model.encode(truncated_texts, 
                                                show_progress_bar=True,
                                                batch_size=32)
        return embeddings
    
    def cluster_problems(self, problem_texts: List[Dict], n_clusters: int = 20) -> List[List[Dict]]:
        """Cluster similar problems together"""
        print(f"🎯 Clustering problems into {n_clusters} groups...")
        
        # Create embeddings
        texts = [item['text'] for item in problem_texts]
        embeddings = self.create_embeddings(texts)
        
        # Cluster embeddings
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Group problems by cluster
        clusters = [[] for _ in range(n_clusters)]
        for i, label in enumerate(cluster_labels):
            clusters[label].append(problem_texts[i])
        
        # Sort clusters by total score (popularity)
        clusters.sort(key=lambda cluster: sum(item['score'] for item in cluster), reverse=True)
        
        # Filter out tiny clusters
        significant_clusters = [cluster for cluster in clusters if len(cluster) >= 3]
        
        print(f"✅ Created {len(significant_clusters)} significant problem clusters")
        return significant_clusters
    
    def analyze_cluster_with_ai(self, cluster: List[Dict]) -> Dict:
        """Analyze a cluster of similar problems with AI"""
        
        # Get representative samples (highest scored + diverse)
        cluster_sorted = sorted(cluster, key=lambda x: x['score'], reverse=True)
        samples = cluster_sorted[:5]  # Top 5 by score
        
        # Create prompt
        sample_texts = "\n\n".join([
            f"Text {i+1} (Score: {item['score']}): {item['text'][:300]}..."
            for i, item in enumerate(samples)
        ])
        
        prompt = f"""
Analyze this cluster of similar Reddit problems and extract business insights:

CLUSTER DATA:
- Total similar problems: {len(cluster)}
- Average score: {sum(item['score'] for item in cluster) / len(cluster):.1f}
- Subreddits: {', '.join(set(item['subreddit'] for item in cluster))}

SAMPLE PROBLEM TEXTS:
{sample_texts}

Please analyze and respond in JSON format:
{{
    "problem_summary": "Brief description of the main problem theme",
    "problem_category": "Category (e.g., financial, productivity, technical)",
    "pain_level": 7,
    "frequency_score": 8,
    "target_audience": "Who has this problem",
    "potential_solutions": ["solution 1", "solution 2"],
    "business_opportunity": "Is this a viable business opportunity? Why?",
    "market_size_estimate": "small/medium/large",
    "implementation_difficulty": "easy/medium/hard",
    "revenue_potential": "low/medium/high"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper and faster
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            
            # Parse JSON response
            if ai_response.startswith('```json'):
                ai_response = ai_response.strip('```json').strip('```')
            
            analysis = json.loads(ai_response)
            
            # Add metadata
            analysis.update({
                'cluster_size': len(cluster),
                'total_score': sum(item['score'] for item in cluster),
                'avg_score': sum(item['score'] for item in cluster) / len(cluster),
                'subreddits': list(set(item['subreddit'] for item in cluster)),
                'sample_texts': [item['text'][:200] + "..." for item in samples[:3]]
            })
            
            return analysis
            
        except Exception as e:
            print(f"    ⚠️  Error analyzing cluster: {e}")
            return {
                'problem_summary': 'Analysis failed',
                'cluster_size': len(cluster),
                'error': str(e)
            }
    
    def rank_opportunities(self, analyses: List[Dict]) -> List[Dict]:
        """Rank business opportunities by potential"""
        print(f"📊 Ranking {len(analyses)} business opportunities...")
        
        # Calculate opportunity scores
        for analysis in analyses:
            if 'error' in analysis:
                analysis['opportunity_score'] = 0
                continue
                
            # Scoring factors
            pain_score = analysis.get('pain_level', 5)
            frequency_score = analysis.get('frequency_score', 5) 
            cluster_size = analysis.get('cluster_size', 1)
            avg_score = analysis.get('avg_score', 1)
            
            # Revenue potential mapping
            revenue_map = {'low': 1, 'medium': 3, 'high': 5}
            revenue_score = revenue_map.get(analysis.get('revenue_potential', 'medium'), 3)
            
            # Market size mapping  
            market_map = {'small': 1, 'medium': 3, 'large': 5}
            market_score = market_map.get(analysis.get('market_size_estimate', 'medium'), 3)
            
            # Implementation difficulty (lower is better)
            impl_map = {'easy': 3, 'medium': 2, 'hard': 1}
            impl_score = impl_map.get(analysis.get('implementation_difficulty', 'medium'), 2)
            
            # Combined opportunity score
            opportunity_score = (
                pain_score * 2 +           # Pain is important
                frequency_score * 1.5 +   # Frequency matters
                np.log(cluster_size) * 2 + # Cluster size (with diminishing returns)
                revenue_score * 2 +        # Revenue potential
                market_score * 1.5 +       # Market size
                impl_score * 1             # Implementation ease
            )
            
            analysis['opportunity_score'] = round(opportunity_score, 2)
        
        # Sort by opportunity score
        analyses.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
        
        return analyses
    
    def generate_report(self, opportunities: List[Dict]) -> str:
        """Generate comprehensive business opportunities report"""
        
        valid_opportunities = [opp for opp in opportunities if 'error' not in opp]
        
        report = f"""# 🚀 AI-Discovered Business Opportunities Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Source:** Reddit harvest analysis with embedding-based clustering
**Analysis Method:** Smart clustering + GPT-4 analysis

## 📊 Executive Summary

- **Total Problem Clusters Analyzed:** {len(opportunities)}
- **Viable Business Opportunities:** {len(valid_opportunities)}
- **Analysis Method:** Embedding similarity clustering + AI analysis
- **Confidence Level:** High (clustered similar problems for accuracy)

## 🔥 Top Business Opportunities

"""
        
        for i, opp in enumerate(valid_opportunities[:10], 1):
            if 'error' in opp:
                continue
                
            report += f"""
### {i}. {opp.get('problem_summary', 'Unknown Problem')}

**📈 Opportunity Score:** {opp.get('opportunity_score', 0)}/100
**📊 Problem Frequency:** {opp.get('cluster_size', 0)} similar reports
**😣 Pain Level:** {opp.get('pain_level', 0)}/10
**💰 Revenue Potential:** {opp.get('revenue_potential', 'unknown').title()}
**🎯 Market Size:** {opp.get('market_size_estimate', 'unknown').title()}
**⚙️ Implementation:** {opp.get('implementation_difficulty', 'unknown').title()}

**🎯 Target Audience:** {opp.get('target_audience', 'Not specified')}

**💡 Potential Solutions:**
"""
            for solution in opp.get('potential_solutions', []):
                report += f"- {solution}\n"
            
            report += f"""
**🏢 Business Opportunity:** {opp.get('business_opportunity', 'Not analyzed')}

**📍 Found in Communities:** {', '.join(opp.get('subreddits', []))}

**📝 Sample Problems:**
"""
            for sample in opp.get('sample_texts', []):
                report += f"- {sample}\n"
            
            report += "\n---\n"
        
        # Add methodology section
        report += f"""
## 🔬 Methodology

1. **Data Collection:** Harvested Reddit posts and comments
2. **Problem Detection:** Identified texts with problem indicators
3. **Embedding Clustering:** Used sentence-transformers to group similar problems
4. **AI Analysis:** GPT-4 analyzed each cluster for business potential
5. **Scoring:** Multi-factor scoring based on pain, frequency, market size, etc.

## 📊 Data Statistics

- **Total Problems Clustered:** {sum(opp.get('cluster_size', 0) for opp in valid_opportunities)}
- **Communities Analyzed:** {len(set(sub for opp in valid_opportunities for sub in opp.get('subreddits', [])))}
- **Average Cluster Size:** {np.mean([opp.get('cluster_size', 0) for opp in valid_opportunities]):.1f}

*This report identifies real problems discussed by real people - these are validated pain points with potential market demand.*
"""
        
        return report
    
    def save_results(self, opportunities: List[Dict]) -> None:
        """Save analysis results"""
        print(f"💾 Saving analysis results...")
        
        os.makedirs('output', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save opportunities
        with open(f'output/smart_opportunities_{timestamp}.json', 'w') as f:
            json.dump(opportunities, f, indent=2)
        
        # Save report
        report = self.generate_report(opportunities)
        with open(f'output/opportunities_report_{timestamp}.md', 'w') as f:
            f.write(report)
        
        print(f"✅ Results saved to output/opportunities_report_{timestamp}.md")
    
    def analyze_harvest(self, max_problems: int = 1000, n_clusters: int = 15) -> None:
        """Complete smart analysis pipeline"""
        print("🚀 STARTING SMART AI PROBLEM ANALYSIS")
        print("=" * 60)
        
        # Step 1: Load data
        self.load_harvest_data()
        if not self.data:
            return
        
        # Step 2: Extract problem texts
        problem_texts = self.extract_problem_texts()
        if not problem_texts:
            print("❌ No problem statements found")
            return
            
        # Limit for processing
        if len(problem_texts) > max_problems:
            print(f"📉 Limiting to top {max_problems} problems by score")
            problem_texts = problem_texts[:max_problems]
        
        # Step 3: Cluster similar problems
        clusters = self.cluster_problems(problem_texts, n_clusters)
        
        # Step 4: Analyze each cluster with AI
        print(f"🤖 Analyzing {len(clusters)} clusters with AI...")
        opportunities = []
        
        for i, cluster in enumerate(clusters, 1):
            print(f"  🧠 Analyzing cluster {i}/{len(clusters)} ({len(cluster)} problems)...")
            analysis = self.analyze_cluster_with_ai(cluster)
            opportunities.append(analysis)
        
        # Step 5: Rank opportunities
        ranked_opportunities = self.rank_opportunities(opportunities)
        
        # Step 6: Save results
        self.save_results(ranked_opportunities)
        
        # Step 7: Print summary
        valid_opps = [opp for opp in ranked_opportunities if 'error' not in opp]
        print(f"\n🎉 SMART ANALYSIS COMPLETE!")
        print(f"📊 Analyzed {len(problem_texts)} problems in {len(clusters)} clusters")
        print(f"🔥 Found {len(valid_opps)} viable business opportunities")
        
        if valid_opps:
            print(f"\n🏆 TOP 3 OPPORTUNITIES:")
            for i, opp in enumerate(valid_opps[:3], 1):
                print(f"{i}. {opp.get('problem_summary', 'Unknown')}")
                print(f"   Score: {opp.get('opportunity_score', 0)} | "
                      f"Pain: {opp.get('pain_level', 0)}/10 | "
                      f"Size: {opp.get('cluster_size', 0)} problems")

if __name__ == "__main__":
    import sys
    
    analyzer = SmartProblemAnalyzer()
    
    # Parse command line arguments
    max_problems = 1000
    n_clusters = 15
    
    if len(sys.argv) > 1:
        max_problems = int(sys.argv[1])
    if len(sys.argv) > 2:
        n_clusters = int(sys.argv[2])
    
    analyzer.analyze_harvest(max_problems, n_clusters)
