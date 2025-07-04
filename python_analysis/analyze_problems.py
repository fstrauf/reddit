#!/usr/bin/env python3
"""
Smart AI Problem Analyzer - Uses embeddings to cluster similar problems first
Then analyzes representative samples with GPT-4 for business opportunities
"""

import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import silhouette_score
import openai
from textblob import TextBlob
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env.local')

class SmartProblemAnalyzer:
    """Enhanced smart problem analyzer with cost optimization and comprehensive analysis"""
    
    def __init__(self, config_file: str = 'config.json'):
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Setup OpenAI
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = openai.OpenAI(api_key=self.openai_key)
        
        # Setup embedding model (lightweight, fast)
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize tracking variables
        self.data = []
        self.api_calls = 0
        self.skipped_clusters = 0
        self.start_time = time.time()
        self.incremental_state = None
        
        # Initialize incremental analyzer if enabled
        if self.config['incremental']['enable_incremental']:
            self.incremental_state = self.load_incremental_state()
    
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Config file {config_file} not found, using defaults")
            return {
                'analysis': {'min_problem_confidence': 0.35, 'min_cluster_size_for_ai': 5},
                'cost_optimization': {'enable_smart_filtering': True},
                'sentiment': {'negative_threshold': -0.1},
                'visualization': {'enable_charts': True},
                'incremental': {'enable_incremental': False},
                'temporal': {'enable_temporal_analysis': True}
            }
    
    def load_incremental_state(self) -> Dict:
        """Load incremental analysis state"""
        state_file = self.config['incremental']['state_file']
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                return json.load(f)
        return {'last_analysis': 0, 'analyzed_ids': set()}
    
    def save_incremental_state(self) -> None:
        """Save incremental analysis state"""
        if self.incremental_state:
            state_file = self.config['incremental']['state_file']
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            # Convert set to list for JSON serialization
            state_to_save = self.incremental_state.copy()
            if isinstance(state_to_save.get('analyzed_ids'), set):
                state_to_save['analyzed_ids'] = list(state_to_save['analyzed_ids'])
            
            with open(state_file, 'w') as f:
                json.dump(state_to_save, f)
        
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
        """Extract problem-related texts with metadata and sentiment analysis"""
        print(f"🔍 Extracting problem statements with enhanced filtering...")
        
        # Problem indicators
        problem_indicators = [
            'problem', 'issue', 'struggle', 'difficult', 'hard', 'annoying', 'frustrating',
            'hate', 'terrible', 'awful', 'sucks', 'broken', 'doesnt work', "doesn't work",
            'bug', 'error', 'fail', 'crash', 'slow', 'expensive', 'waste', 'time consuming',
            'wish there was', 'need a solution', 'looking for', 'help with', 'stuck with',
            'cant find', 'no way to', 'impossible', 'ridiculous', 'pain', 'nightmare'
        ]
        
        # Emotion keywords for enhanced detection
        frustration_words = ['frustrated', 'annoying', 'irritating', 'sick of', 'fed up']
        urgency_words = ['urgent', 'asap', 'desperate', 'please help', 'need help']
        
        problem_texts = []
        
        for post in self.data:
            # Check post title and selftext
            post_text = f"{post['title']} {post['selftext']}".strip()
            
            if len(post_text) > 50:
                # Enhanced problem detection
                has_problem_indicator = any(indicator in post_text.lower() for indicator in problem_indicators)
                
                if has_problem_indicator:
                    # Sentiment analysis
                    blob = TextBlob(post_text)
                    sentiment = {
                        'polarity': blob.sentiment.polarity,  # -1 (negative) to 1 (positive)
                        'subjectivity': blob.sentiment.subjectivity  # 0 (objective) to 1 (subjective)
                    }
                    
                    # Calculate problem confidence score
                    problem_confidence = self._calculate_problem_confidence(
                        post_text, sentiment, post['score'], post.get('num_comments', 0)
                    )
                    
                    # Calculate engagement score
                    engagement = self._calculate_engagement_score(
                        post['score'], post.get('num_comments', 0), post.get('upvote_ratio', 0.5)
                    )
                    
                    # Enhanced metadata
                    problem_data = {
                        'text': post_text,
                        'type': 'post',
                        'score': post['score'],
                        'subreddit': post['subreddit'],
                        'post_id': post['id'],
                        'upvote_ratio': post.get('upvote_ratio', 0.5),
                        'num_comments': post.get('num_comments', 0),
                        'sentiment': sentiment,
                        'problem_confidence': problem_confidence,
                        'engagement': engagement,
                        'has_frustration': any(word in post_text.lower() for word in frustration_words),
                        'has_urgency': any(word in post_text.lower() for word in urgency_words)
                    }
                    
                    # Only add if it meets quality thresholds
                    if problem_confidence > 0.3 and sentiment['polarity'] < 0.2:  # Negative or neutral sentiment
                        problem_texts.append(problem_data)
            
            # Check comments with enhanced filtering
            for comment in post['comments']:
                if (len(comment['text']) > 30 and 
                    comment['score'] > 0):  # Only positive score comments
                    
                    has_problem_indicator = any(indicator in comment['text'].lower() for indicator in problem_indicators)
                    
                    if has_problem_indicator:
                        # Sentiment analysis for comment
                        blob = TextBlob(comment['text'])
                        sentiment = {
                            'polarity': blob.sentiment.polarity,
                            'subjectivity': blob.sentiment.subjectivity
                        }
                        
                        # Calculate problem confidence for comment
                        problem_confidence = self._calculate_problem_confidence(
                            comment['text'], sentiment, comment['score'], 0
                        )
                        
                        if problem_confidence > 0.25 and sentiment['polarity'] < 0.3:
                            problem_texts.append({
                                'text': comment['text'],
                                'type': 'comment', 
                                'score': comment['score'],
                                'subreddit': post['subreddit'],
                                'post_id': post['id'],
                                'comment_id': comment['id'],
                                'sentiment': sentiment,
                                'problem_confidence': problem_confidence,
                                'engagement': comment['score'],  # Simple engagement for comments
                                'has_frustration': any(word in comment['text'].lower() for word in frustration_words),
                                'has_urgency': any(word in comment['text'].lower() for word in urgency_words)
                            })
        
        # Sort by problem confidence and engagement
        problem_texts.sort(key=lambda x: x['problem_confidence'] * x['engagement'], reverse=True)
        
        # Print enhanced statistics
        if problem_texts:
            avg_sentiment = sum(p['sentiment']['polarity'] for p in problem_texts) / len(problem_texts)
            avg_confidence = sum(p['problem_confidence'] for p in problem_texts) / len(problem_texts)
            frustration_count = sum(1 for p in problem_texts if p['has_frustration'])
            urgency_count = sum(1 for p in problem_texts if p['has_urgency'])
            
            print(f"🎯 Found {len(problem_texts)} high-quality problem statements")
            print(f"📊 Average sentiment: {avg_sentiment:.2f} (negative is better for problems)")
            print(f"🎯 Average confidence: {avg_confidence:.2f}")
            print(f"😤 Frustration indicators: {frustration_count} ({frustration_count/len(problem_texts)*100:.1f}%)")
            print(f"🚨 Urgency indicators: {urgency_count} ({urgency_count/len(problem_texts)*100:.1f}%)")
        
        return problem_texts
    
    def _calculate_problem_confidence(self, text: str, sentiment: Dict, score: int, num_comments: int) -> float:
        """Calculate confidence that this text represents a real problem"""
        confidence = 0.0
        text_lower = text.lower()
        
        # Sentiment factor (negative sentiment = higher confidence)
        if sentiment['polarity'] < -0.1:
            confidence += 0.3
        elif sentiment['polarity'] < 0.1:
            confidence += 0.2
        
        # Subjectivity factor (subjective = higher confidence for problems)
        confidence += sentiment['subjectivity'] * 0.2
        
        # Problem intensity keywords
        intensity_words = ['hate', 'terrible', 'awful', 'nightmare', 'impossible', 'ridiculous']
        if any(word in text_lower for word in intensity_words):
            confidence += 0.2
        
        # Solution seeking keywords
        solution_words = ['help', 'solution', 'fix', 'solve', 'advice']
        if any(word in text_lower for word in solution_words):
            confidence += 0.15
        
        # Engagement factor (normalized)
        engagement_factor = min(score / 10.0, 0.15)  # Cap at 0.15
        confidence += engagement_factor
        
        # Comment engagement factor
        if num_comments > 5:
            confidence += 0.1
        
        # Text length factor (longer posts often have more context)
        if len(text) > 200:
            confidence += 0.05
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def get_new_problems(self, all_problems: List[Dict]) -> List[Dict]:
        """Get only problems not yet analyzed (incremental analysis)"""
        if not self.config['incremental']['enable_incremental'] or not self.incremental_state:
            return all_problems
        
        analyzed_ids = set(self.incremental_state.get('analyzed_ids', []))
        new_problems = []
        
        for problem in all_problems:
            problem_id = f"{problem.get('post_id', '')}_{problem.get('comment_id', '')}"
            if problem_id not in analyzed_ids:
                new_problems.append(problem)
                analyzed_ids.add(problem_id)
        
        # Update state
        self.incremental_state['analyzed_ids'] = analyzed_ids
        self.incremental_state['last_analysis'] = time.time()
        
        print(f"📊 Incremental: {len(new_problems)} new problems since last analysis")
        return new_problems
    
    def analyze_temporal_patterns(self, problem_texts: List[Dict]) -> Dict:
        """Analyze when problems are posted"""
        if not self.config['temporal']['enable_temporal_analysis']:
            return {}
        
        print("🕐 Analyzing temporal patterns...")
        
        # Convert timestamps to datetime
        temporal_data = []
        for problem in problem_texts:
            if 'created_utc' in problem:
                temporal_data.append({
                    'datetime': pd.to_datetime(problem['created_utc'], unit='s'),
                    'text': problem['text'],
                    'score': problem['score']
                })
        
        if not temporal_data:
            return {}
        
        df = pd.DataFrame(temporal_data)
        df['hour'] = df['datetime'].dt.hour
        df['dayofweek'] = df['datetime'].dt.dayofweek
        df['is_weekend'] = df['dayofweek'].isin([5, 6])
        
        # Find peak problem hours/days
        hourly_problems = df.groupby('hour').size()
        daily_problems = df.groupby('dayofweek').size()
        
        # Weekend vs weekday analysis
        weekend_problems = df[df['is_weekend']].shape[0]
        weekday_problems = df[~df['is_weekend']].shape[0]
        
        return {
            'peak_hour': int(hourly_problems.idxmax()) if len(hourly_problems) > 0 else 0,
            'peak_day': int(daily_problems.idxmax()) if len(daily_problems) > 0 else 0,
            'weekend_problems': weekend_problems,
            'weekday_problems': weekday_problems,
            'weekend_ratio': weekend_problems / (weekend_problems + weekday_problems) if (weekend_problems + weekday_problems) > 0 else 0,
            'hourly_distribution': hourly_problems.to_dict(),
            'daily_distribution': daily_problems.to_dict()
        }
    
    def analyze_user_patterns(self, problem_texts: List[Dict]) -> Dict:
        """Analyze who posts problems"""
        print("👥 Analyzing user patterns...")
        
        authors = [p.get('author', '[deleted]') for p in problem_texts]
        author_counts = Counter(authors)
        
        # Find repeat problem posters
        repeat_posters = {k: v for k, v in author_counts.items() if v > 1 and k != '[deleted]'}
        
        return {
            'unique_authors': len(set(authors)),
            'repeat_posters': len(repeat_posters),
            'most_problems_by_user': max(author_counts.values()) if author_counts else 0,
            'deleted_users': author_counts.get('[deleted]', 0),
            'avg_problems_per_user': sum(author_counts.values()) / len(author_counts) if author_counts else 0
        }
    
    def map_emotions(self, problem_texts: List[Dict]) -> Dict:
        """Map emotional patterns in problems"""
        print("😊 Mapping emotional patterns...")
        
        emotion_keywords = {
            'frustration': ['frustrated', 'annoying', 'irritating', 'sick of'],
            'anger': ['angry', 'pissed', 'furious', 'hate'],
            'confusion': ['confused', 'dont understand', 'lost', 'no idea'],
            'desperation': ['desperate', 'please help', 'urgent', 'asap'],
            'disappointment': ['disappointed', 'let down', 'expected better']
        }
        
        emotion_counts = {emotion: 0 for emotion in emotion_keywords}
        emotion_examples = {emotion: [] for emotion in emotion_keywords}
        
        for item in problem_texts:
            text_lower = item['text'].lower()
            for emotion, keywords in emotion_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        emotion_counts[emotion] += 1
                        if len(emotion_examples[emotion]) < 3:  # Store examples
                            emotion_examples[emotion].append(item['text'][:100] + "...")
                        break
        
        return {
            'emotion_counts': emotion_counts,
            'emotion_examples': emotion_examples,
            'total_emotional_problems': sum(emotion_counts.values()),
            'emotion_ratio': sum(emotion_counts.values()) / len(problem_texts) if problem_texts else 0
        }
    
    def _calculate_engagement_score(self, score: int, num_comments: int, upvote_ratio: float) -> float:
        """Calculate engagement score for prioritization"""
        # Combine score, comments, and upvote ratio
        engagement = score + (num_comments * 2) + (upvote_ratio * 10)
        return max(engagement, 1.0)  # Minimum engagement of 1
    
    def should_analyze_cluster_with_ai(self, cluster: List[Dict]) -> bool:
        """Determine if cluster should be analyzed with AI (cost optimization)"""
        if not self.config['cost_optimization']['enable_smart_filtering']:
            return True
        
        # Check API call limits
        max_calls = self.config['analysis'].get('max_api_calls', 50)
        if self.api_calls >= max_calls:
            return False
        
        # Check cluster size threshold
        min_size = self.config['analysis'].get('min_cluster_size_for_ai', 5)
        if len(cluster) < min_size:
            return False
        
        # Check engagement threshold
        min_engagement = self.config['analysis'].get('min_engagement_for_ai', 50)
        total_engagement = sum(item.get('engagement', 0) for item in cluster)
        if total_engagement < min_engagement:
            return False
        
        # Check average problem confidence
        min_confidence = self.config['analysis'].get('min_problem_confidence', 0.35)
        avg_confidence = sum(item.get('problem_confidence', 0) for item in cluster) / len(cluster)
        if avg_confidence < min_confidence:
            return False
        
        return True
    
    def track_api_usage(self) -> Dict:
        """Track API usage and cost savings"""
        estimated_cost = self.api_calls * self.config['cost_optimization'].get('estimated_cost_per_call', 0.002)
        estimated_savings = self.skipped_clusters * self.config['cost_optimization'].get('estimated_cost_per_call', 0.002)
        
        return {
            'api_calls_made': self.api_calls,
            'api_calls_saved': self.skipped_clusters,
            'estimated_cost': round(estimated_cost, 4),
            'estimated_savings': round(estimated_savings, 4),
            'total_clusters_processed': self.api_calls + self.skipped_clusters,
            'efficiency_ratio': self.skipped_clusters / (self.api_calls + self.skipped_clusters) if (self.api_calls + self.skipped_clusters) > 0 else 0
        }
    
    def create_problem_visualizations(self, problem_texts: List[Dict], clusters: List[List[Dict]], 
                                    temporal_analysis: Dict, emotion_analysis: Dict, user_analysis: Dict) -> None:
        """Create comprehensive visualizations of problem patterns"""
        if not self.config['visualization']['enable_charts']:
            return
        
        print("📊 Creating visualizations...")
        os.makedirs('output/charts', exist_ok=True)
        
        try:
            # 1. Sentiment Distribution
            plt.figure(figsize=(12, 6))
            sentiments = [p['sentiment']['polarity'] for p in problem_texts if 'sentiment' in p]
            if sentiments:
                plt.hist(sentiments, bins=50, alpha=0.7, color='red', edgecolor='black')
                plt.title('Problem Sentiment Distribution', fontsize=16, fontweight='bold')
                plt.xlabel('Sentiment Score (Negative ← → Positive)')
                plt.ylabel('Number of Problems')
                plt.axvline(x=0, color='black', linestyle='--', alpha=0.5, label='Neutral')
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig('output/charts/sentiment_distribution.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            # 2. Cluster Sizes
            plt.figure(figsize=(12, 6))
            cluster_sizes = [len(c) for c in clusters]
            if cluster_sizes:
                plt.bar(range(len(cluster_sizes)), cluster_sizes, color='skyblue', edgecolor='navy')
                plt.title('Problem Cluster Sizes', fontsize=16, fontweight='bold')
                plt.xlabel('Cluster ID')
                plt.ylabel('Number of Problems')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig('output/charts/cluster_sizes.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            # 3. Engagement vs Sentiment Scatter
            plt.figure(figsize=(12, 8))
            max_points = self.config['visualization'].get('max_scatter_points', 500)
            sample_problems = problem_texts[:max_points]
            
            if sample_problems:
                engagements = [p.get('engagement', 0) for p in sample_problems]
                sentiments = [p['sentiment']['polarity'] for p in sample_problems if 'sentiment' in p]
                
                if len(engagements) == len(sentiments):
                    scatter = plt.scatter(sentiments, engagements, alpha=0.6, c=sentiments, 
                                        cmap='RdYlBu_r', s=30)
                    plt.colorbar(scatter, label='Sentiment Score')
                    plt.xlabel('Sentiment Score')
                    plt.ylabel('Engagement Score')
                    plt.title('Problem Engagement vs Sentiment', fontsize=16, fontweight='bold')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    plt.savefig('output/charts/engagement_sentiment.png', dpi=300, bbox_inches='tight')
                    plt.close()
            
            # 4. Temporal Analysis Charts
            if temporal_analysis and 'hourly_distribution' in temporal_analysis:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
                
                # Hourly distribution
                hours = list(temporal_analysis['hourly_distribution'].keys())
                counts = list(temporal_analysis['hourly_distribution'].values())
                ax1.bar(hours, counts, color='orange', alpha=0.7)
                ax1.set_title('Problems by Hour of Day', fontweight='bold')
                ax1.set_xlabel('Hour')
                ax1.set_ylabel('Number of Problems')
                ax1.grid(True, alpha=0.3)
                
                # Daily distribution
                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                daily_counts = [temporal_analysis['daily_distribution'].get(i, 0) for i in range(7)]
                ax2.bar(days, daily_counts, color='green', alpha=0.7)
                ax2.set_title('Problems by Day of Week', fontweight='bold')
                ax2.set_ylabel('Number of Problems')
                ax2.grid(True, alpha=0.3)
                
                plt.tight_layout()
                plt.savefig('output/charts/temporal_patterns.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            # 5. Emotion Analysis
            if emotion_analysis and 'emotion_counts' in emotion_analysis:
                plt.figure(figsize=(12, 6))
                emotions = list(emotion_analysis['emotion_counts'].keys())
                counts = list(emotion_analysis['emotion_counts'].values())
                
                colors = ['red', 'orange', 'yellow', 'purple', 'blue']
                plt.bar(emotions, counts, color=colors[:len(emotions)], alpha=0.7)
                plt.title('Emotional Patterns in Problems', fontsize=16, fontweight='bold')
                plt.xlabel('Emotion Type')
                plt.ylabel('Number of Problems')
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig('output/charts/emotion_patterns.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            # 6. Word Cloud of Problems
            all_text = ' '.join([p['text'] for p in problem_texts[:500]])  # Limit for performance
            if all_text:
                wordcloud = WordCloud(width=800, height=400, background_color='white',
                                    max_words=100, colormap='Reds').generate(all_text)
                
                plt.figure(figsize=(12, 6))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                plt.title('Most Common Words in Problems', fontsize=16, fontweight='bold', pad=20)
                plt.tight_layout()
                plt.savefig('output/charts/problem_wordcloud.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            print("✅ Visualizations saved to output/charts/")
            
        except Exception as e:
            print(f"⚠️  Error creating visualizations: {e}")
    
    def optimize_cluster_count(self, embeddings: np.ndarray, max_clusters: int = 30) -> int:
        """Dynamically determine optimal number of clusters using silhouette analysis"""
        if not self.config['cost_optimization']['enable_dynamic_clustering']:
            return self.config['analysis'].get('n_clusters', 15)
        
        print("🔍 Optimizing cluster count...")
        
        best_score = -1
        best_k = self.config['analysis'].get('n_clusters', 15)
        
        # Test different cluster counts
        for k in range(3, min(max_clusters, len(embeddings) // 2)):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=5)
                cluster_labels = kmeans.fit_predict(embeddings)
                score = silhouette_score(embeddings, cluster_labels)
                
                if score > best_score:
                    best_score = score
                    best_k = k
                    
            except Exception:
                continue
        
        print(f"🎯 Optimal clusters: {best_k} (silhouette score: {best_score:.3f})")
        return best_k
    
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
        """Cluster similar problems together with dynamic optimization"""
        
        # Create embeddings
        texts = [item['text'] for item in problem_texts]
        embeddings = self.create_embeddings(texts)
        
        # Optimize cluster count if enabled
        optimal_clusters = self.optimize_cluster_count(embeddings, n_clusters)
        print(f"🎯 Clustering problems into {optimal_clusters} groups...")
        
        # Cluster embeddings
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Group problems by cluster
        clusters = [[] for _ in range(optimal_clusters)]
        for i, label in enumerate(cluster_labels):
            clusters[label].append(problem_texts[i])
        
        # Sort clusters by combined score (popularity + engagement + confidence)
        def cluster_priority(cluster):
            total_score = sum(item['score'] for item in cluster)
            total_engagement = sum(item.get('engagement', 0) for item in cluster)
            avg_confidence = sum(item.get('problem_confidence', 0) for item in cluster) / len(cluster)
            return total_score + total_engagement + (avg_confidence * 100)
        
        clusters.sort(key=cluster_priority, reverse=True)
        
        # Filter out tiny clusters
        min_cluster_size = max(3, self.config['analysis'].get('min_cluster_size_for_ai', 5) // 2)
        significant_clusters = [cluster for cluster in clusters if len(cluster) >= min_cluster_size]
        
        print(f"✅ Created {len(significant_clusters)} significant problem clusters")
        return significant_clusters
    
    def analyze_cluster_with_ai(self, cluster: List[Dict]) -> Dict:
        """Analyze a cluster of similar problems with AI (with cost optimization)"""
        
        # Check if we should analyze this cluster with AI
        if not self.should_analyze_cluster_with_ai(cluster):
            self.skipped_clusters += 1
            
            # Return basic analysis without AI
            avg_sentiment = sum(item['sentiment']['polarity'] for item in cluster if 'sentiment' in item) / len(cluster)
            subreddits = list(set(item['subreddit'] for item in cluster))
            
            return {
                'problem_summary': f'Problem cluster (sentiment: {avg_sentiment:.2f})',
                'cluster_size': len(cluster),
                'total_score': sum(item['score'] for item in cluster),
                'avg_score': sum(item['score'] for item in cluster) / len(cluster),
                'subreddits': subreddits,
                'skipped_ai_analysis': True,
                'skip_reason': 'Did not meet AI analysis criteria',
                'avg_sentiment': avg_sentiment
            }
        
        # Proceed with AI analysis
        self.api_calls += 1
        
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
    
    def generate_report(self, opportunities: List[Dict], temporal_analysis: Dict = None, 
                       emotion_analysis: Dict = None, user_analysis: Dict = None) -> str:
        """Generate comprehensive business opportunities report with enhanced insights"""
        
        valid_opportunities = [opp for opp in opportunities if 'error' not in opp and not opp.get('skipped_ai_analysis', False)]
        skipped_opportunities = [opp for opp in opportunities if opp.get('skipped_ai_analysis', False)]
        api_usage = self.track_api_usage()
        
        report = f"""# 🚀 Enhanced AI-Discovered Business Opportunities Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Source:** Reddit harvest analysis with embedding-based clustering
**Analysis Method:** Smart clustering + GPT-4 analysis + Enhanced Analytics

## 📊 Executive Summary

- **Total Problem Clusters Analyzed:** {len(opportunities)}
- **AI-Analyzed Opportunities:** {len(valid_opportunities)}
- **Cost-Optimized Skipped Clusters:** {len(skipped_opportunities)}
- **API Calls Made:** {api_usage['api_calls_made']}
- **API Calls Saved:** {api_usage['api_calls_saved']}
- **Estimated Cost:** ${api_usage['estimated_cost']}
- **Estimated Savings:** ${api_usage['estimated_savings']}
- **Cost Efficiency:** {api_usage['efficiency_ratio']*100:.1f}% of clusters skipped

## 🎯 Enhanced Analytics Insights
"""
        
        # Add temporal insights
        if temporal_analysis:
            peak_hour = temporal_analysis.get('peak_hour', 'N/A')
            weekend_ratio = temporal_analysis.get('weekend_ratio', 0) * 100
            report += f"""
### ⏰ Temporal Patterns
- **Peak Problem Hour:** {peak_hour}:00
- **Weekend vs Weekday:** {weekend_ratio:.1f}% problems posted on weekends
- **Problem Distribution:** Check charts for detailed hourly/daily patterns
"""
        
        # Add emotion insights
        if emotion_analysis:
            total_emotional = emotion_analysis.get('total_emotional_problems', 0)
            emotion_ratio = emotion_analysis.get('emotion_ratio', 0) * 100
            top_emotions = sorted(emotion_analysis['emotion_counts'].items(), key=lambda x: x[1], reverse=True)[:3]
            
            report += f"""
### 😊 Emotional Analysis
- **Problems with Emotional Indicators:** {total_emotional} ({emotion_ratio:.1f}%)
- **Top Emotions:** {', '.join([f'{emotion} ({count})' for emotion, count in top_emotions])}
- **Emotional Intensity:** Higher emotional problems often indicate stronger pain points
"""
        
        # Add user insights
        if user_analysis:
            report += f"""
### 👥 User Behavior Patterns
- **Unique Problem Reporters:** {user_analysis.get('unique_authors', 0)}
- **Repeat Problem Posters:** {user_analysis.get('repeat_posters', 0)}
- **Average Problems per User:** {user_analysis.get('avg_problems_per_user', 0):.1f}
"""

        report += "\n## 🔥 Top Business Opportunities\n"
        
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
    
    def save_results(self, opportunities: List[Dict], temporal_analysis: Dict = None, 
                    emotion_analysis: Dict = None, user_analysis: Dict = None) -> None:
        """Save enhanced analysis results"""
        print(f"💾 Saving enhanced analysis results...")
        
        os.makedirs('output', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save opportunities with metadata
        full_results = {
            'opportunities': opportunities,
            'temporal_analysis': temporal_analysis or {},
            'emotion_analysis': emotion_analysis or {},
            'user_analysis': user_analysis or {},
            'api_usage': self.track_api_usage(),
            'analysis_metadata': {
                'timestamp': timestamp,
                'total_runtime': time.time() - self.start_time,
                'config_used': self.config
            }
        }
        
        with open(f'output/enhanced_opportunities_{timestamp}.json', 'w') as f:
            json.dump(full_results, f, indent=2)
        
        # Save enhanced report
        report = self.generate_report(opportunities, temporal_analysis, emotion_analysis, user_analysis)
        with open(f'output/enhanced_report_{timestamp}.md', 'w') as f:
            f.write(report)
        
        # Save incremental state
        if self.config['incremental']['enable_incremental']:
            self.save_incremental_state()
        
        print(f"✅ Enhanced results saved:")
        print(f"   📊 Report: output/enhanced_report_{timestamp}.md") 
        print(f"   📋 Data: output/enhanced_opportunities_{timestamp}.json")
        if self.config['visualization']['enable_charts']:
            print(f"   📈 Charts: output/charts/")
    
    def analyze_harvest(self, max_problems: int = 1000, n_clusters: int = 15, enhanced: bool = True) -> None:
        """Complete enhanced analysis pipeline with cost optimization"""
        print("🚀 STARTING ENHANCED AI PROBLEM ANALYSIS")
        print("=" * 60)
        print(f"🎯 Configuration: Enhanced={enhanced}, Max API Calls={self.config['analysis'].get('max_api_calls', 50)}")
        print(f"💰 Cost Optimization: {self.config['cost_optimization']['enable_smart_filtering']}")
        
        # Step 1: Load data
        self.load_harvest_data()
        if not self.data:
            return
        
        # Step 2: Extract problem texts with enhanced filtering
        all_problem_texts = self.extract_problem_texts()
        if not all_problem_texts:
            print("❌ No problem statements found")
            return
        
        # Step 3: Apply incremental analysis (only new problems)
        if enhanced and self.config['incremental']['enable_incremental']:
            problem_texts = self.get_new_problems(all_problem_texts)
            if not problem_texts:
                print("✅ No new problems since last analysis")
                return
        else:
            problem_texts = all_problem_texts
            
        # Limit for processing
        max_problems = min(max_problems, self.config['analysis'].get('max_problems', 1000))
        if len(problem_texts) > max_problems:
            print(f"📉 Limiting to top {max_problems} problems by confidence & engagement")
            problem_texts = problem_texts[:max_problems]
        
        # Step 4: Enhanced Analytics (Non-AI)
        temporal_analysis = {}
        emotion_analysis = {}
        user_analysis = {}
        
        if enhanced:
            print("🔍 Running Enhanced Non-AI Analytics...")
            temporal_analysis = self.analyze_temporal_patterns(problem_texts)
            emotion_analysis = self.map_emotions(problem_texts)
            user_analysis = self.analyze_user_patterns(problem_texts)
            
            print(f"📈 Temporal: Peak hour {temporal_analysis.get('peak_hour', 'N/A')}")
            print(f"😊 Emotions: {emotion_analysis.get('total_emotional_problems', 0)} emotional problems")
            print(f"👥 Users: {user_analysis.get('unique_authors', 0)} unique problem reporters")
        
        # Step 5: Smart clustering with optimization
        clusters = self.cluster_problems(problem_texts, n_clusters)
        if not clusters:
            print("❌ No significant clusters found")
            return
        
        # Step 6: AI Analysis with Cost Optimization
        print(f"🤖 Analyzing {len(clusters)} clusters with smart AI filtering...")
        opportunities = []
        
        for i, cluster in enumerate(clusters, 1):
            should_analyze = self.should_analyze_cluster_with_ai(cluster)
            action = "AI ANALYZING" if should_analyze else "SKIPPING"
            
            print(f"  🧠 Cluster {i}/{len(clusters)} ({len(cluster)} problems) - {action}")
            analysis = self.analyze_cluster_with_ai(cluster)
            opportunities.append(analysis)
            
            # Check cost limits
            if self.api_calls >= self.config['analysis'].get('max_api_calls', 50):
                print(f"⚠️  API call limit reached ({self.api_calls} calls)")
                break
        
        # Step 7: Rank opportunities (including skipped ones)
        ranked_opportunities = self.rank_opportunities(opportunities)
        
        # Step 8: Create visualizations
        if enhanced and self.config['visualization']['enable_charts']:
            self.create_problem_visualizations(problem_texts, clusters, temporal_analysis, 
                                             emotion_analysis, user_analysis)
        
        # Step 9: Save enhanced results
        self.save_results(ranked_opportunities, temporal_analysis, emotion_analysis, user_analysis)
        
        # Step 10: Print comprehensive summary
        api_usage = self.track_api_usage()
        valid_opps = [opp for opp in ranked_opportunities if 'error' not in opp and not opp.get('skipped_ai_analysis', False)]
        skipped_opps = [opp for opp in ranked_opportunities if opp.get('skipped_ai_analysis', False)]
        
        print(f"\n🎉 ENHANCED ANALYSIS COMPLETE!")
        print(f"⏱️  Total Runtime: {time.time() - self.start_time:.1f} seconds")
        print(f"📊 Analyzed {len(problem_texts)} problems in {len(clusters)} clusters")
        print(f"🤖 AI-Analyzed Opportunities: {len(valid_opps)}")
        print(f"⚡ Cost-Optimized Skipped: {len(skipped_opps)}")
        print(f"💰 API Calls Made: {api_usage['api_calls_made']} | Saved: {api_usage['api_calls_saved']}")
        print(f"💵 Estimated Cost: ${api_usage['estimated_cost']} | Savings: ${api_usage['estimated_savings']}")
        print(f"📈 Cost Efficiency: {api_usage['efficiency_ratio']*100:.1f}% clusters skipped")
        
        if temporal_analysis:
            print(f"🕐 Peak Problem Time: {temporal_analysis.get('peak_hour', 'N/A')}:00")
            print(f"📅 Weekend Ratio: {temporal_analysis.get('weekend_ratio', 0)*100:.1f}%")
        
        if emotion_analysis:
            top_emotion = max(emotion_analysis['emotion_counts'].items(), key=lambda x: x[1])[0]
            print(f"😊 Top Emotion: {top_emotion} ({emotion_analysis['emotion_counts'][top_emotion]} problems)")
        
        if valid_opps:
            print(f"\n🏆 TOP 3 AI-ANALYZED OPPORTUNITIES:")
            for i, opp in enumerate(valid_opps[:3], 1):
                print(f"{i}. {opp.get('problem_summary', 'Unknown')}")
                print(f"   Score: {opp.get('opportunity_score', 0)} | "
                      f"Pain: {opp.get('pain_level', 0)}/10 | "
                      f"Size: {opp.get('cluster_size', 0)} problems")
        
        if enhanced:
            print(f"\n📈 Enhanced features completed successfully!")
            print(f"   🔍 Check output/charts/ for visualizations")
            print(f"   📊 Full analysis in output/enhanced_report_*.md")

if __name__ == "__main__":
    import sys
    
    # Enhanced command line interface
    parser = argparse.ArgumentParser(description='Enhanced Reddit Problem Analysis with Cost Optimization')
    parser.add_argument('--enhanced', action='store_true', default=True, 
                       help='Enable enhanced analysis features (default: True)')
    parser.add_argument('--basic', action='store_true', 
                       help='Run basic analysis only (disables enhanced features)')
    parser.add_argument('--max-problems', type=int, default=1000,
                       help='Maximum problems to analyze (default: 1000)')
    parser.add_argument('--clusters', type=int, default=15,
                       help='Number of clusters (default: 15)')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--harvest-file', type=str, default='output/latest_harvest.json',
                       help='Harvest file to analyze (default: output/latest_harvest.json)')
    
    args = parser.parse_args()
    
    # Initialize analyzer with config
    try:
        analyzer = SmartProblemAnalyzer(config_file=args.config)
    except Exception as e:
        print(f"❌ Error initializing analyzer: {e}")
        sys.exit(1)
    
    # Override harvest file if specified
    if args.harvest_file != 'output/latest_harvest.json':
        print(f"📂 Using custom harvest file: {args.harvest_file}")
    
    # Determine if enhanced mode should be used
    enhanced_mode = args.enhanced and not args.basic
    
    print(f"🚀 Starting analysis with enhanced mode: {enhanced_mode}")
    print(f"⚙️  Config file: {args.config}")
    print(f"📋 Max problems: {args.max_problems}")
    print(f"🎯 Clusters: {args.clusters}")
    
    try:
        # Load custom harvest file if specified
        if args.harvest_file != 'output/latest_harvest.json':
            analyzer.load_harvest_data(args.harvest_file)
        
        # Run analysis
        analyzer.analyze_harvest(
            max_problems=args.max_problems,
            n_clusters=args.clusters,
            enhanced=enhanced_mode
        )
        
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        # Save current state if incremental is enabled
        if analyzer.config['incremental']['enable_incremental']:
            analyzer.save_incremental_state()
            print("💾 Incremental state saved")
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

