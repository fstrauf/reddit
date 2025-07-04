#!/usr/bin/env python3
"""
Reddit Data Harvester - Simple script to collect Reddit posts and comments
Clean version: Just harvest any subreddit you specify
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import praw
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env.local')

class RedditHarvester:
    """Simple Reddit data harvester"""
    
    def __init__(self):
        self.reddit = self._setup_reddit()
        self.all_data = []
        
    def _setup_reddit(self) -> praw.Reddit:
        """Initialize Reddit API connection"""
        client_id = os.getenv('NUXT_REDDIT_CLIENT_ID')
        client_secret = os.getenv('NUXT_REDDIT_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Reddit API credentials not found in environment variables")
        
        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="RedditHarvester/1.0"
        )
    
    def harvest_subreddit(self, subreddit_name: str, max_posts: int = 800) -> List[Dict]:
        """
        Harvest data from a subreddit
        Gets posts from: hot, new, top (year), top (all time)
        """
        print(f"\n🏗️  HARVESTING r/{subreddit_name}")
        print("=" * 50)
        
        subreddit = self.reddit.subreddit(subreddit_name)
        subreddit_data = []
        
        # Different sorting methods to get maximum coverage
        sorting_methods = [
            ('hot', subreddit.hot(limit=max_posts//4)),
            ('new', subreddit.new(limit=max_posts//4)), 
            ('top_year', subreddit.top(time_filter='year', limit=max_posts//4)),
            ('top_all', subreddit.top(time_filter='all', limit=max_posts//4))
        ]
        
        for sort_name, submissions in sorting_methods:
            print(f"  📥 Collecting {sort_name} posts...")
            
            try:
                for submission in submissions:
                    # Skip if we already have this post
                    if any(post['id'] == submission.id for post in subreddit_data):
                        continue
                        
                    # Collect post data
                    post_data = {
                        'id': submission.id,
                        'title': submission.title,
                        'selftext': submission.selftext,
                        'score': submission.score,
                        'upvote_ratio': submission.upvote_ratio,
                        'num_comments': submission.num_comments,
                        'created_utc': submission.created_utc,
                        'subreddit': subreddit_name,
                        'url': submission.url,
                        'author': str(submission.author) if submission.author else '[deleted]',
                        'sort_method': sort_name,
                        'comments': []
                    }
                    
                    # Collect ALL comments (this is where the gold is)
                    comments = self._harvest_all_comments(submission)
                    post_data['comments'] = comments
                    
                    subreddit_data.append(post_data)
                    
                    if len(subreddit_data) % 50 == 0:
                        print(f"    ✅ Collected {len(subreddit_data)} posts so far...")
                        
            except Exception as e:
                print(f"    ⚠️  Error in {sort_name}: {e}")
                continue
        
        print(f"  🎉 Total collected from r/{subreddit_name}: {len(subreddit_data)} posts")
        return subreddit_data
    
    def _harvest_all_comments(self, submission) -> List[Dict]:
        """Get ALL comments from a submission"""
        comments = []
        
        try:
            # Get all comments (not just top-level)
            submission.comments.replace_more(limit=None)
            
            for comment in submission.comments.list():
                if hasattr(comment, 'body') and comment.body not in ['[deleted]', '[removed]']:
                    comment_data = {
                        'id': comment.id,
                        'text': comment.body,
                        'score': comment.score,
                        'created_utc': comment.created_utc,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'parent_id': comment.parent_id,
                        'depth': comment.depth if hasattr(comment, 'depth') else 0
                    }
                    comments.append(comment_data)
                    
        except Exception as e:
            print(f"      ⚠️  Error collecting comments: {e}")
            
        return comments
    
    def save_data(self, subreddit_name: str) -> str:
        """Save harvested data to file"""
        os.makedirs('output', exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'output/reddit_{subreddit_name}_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.all_data, f, indent=2)
        
        # Also save as latest
        with open('output/latest_harvest.json', 'w') as f:
            json.dump(self.all_data, f, indent=2)
            
        return filename
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the harvested data"""
        if not self.all_data:
            return {"error": "No data harvested yet"}
        
        total_posts = len(self.all_data)
        total_comments = sum(len(post['comments']) for post in self.all_data)
        
        # Calculate date range
        timestamps = [post['created_utc'] for post in self.all_data]
        oldest = datetime.fromtimestamp(min(timestamps))
        newest = datetime.fromtimestamp(max(timestamps))
        
        return {
            'total_posts': total_posts,
            'total_comments': total_comments,
            'total_text_pieces': total_posts + total_comments,
            'date_range': {
                'oldest': oldest.strftime('%Y-%m-%d'),
                'newest': newest.strftime('%Y-%m-%d'),
                'span_days': (newest - oldest).days
            }
        }

def check_existing_data(subreddit_name: str) -> str:
    """Check if we already have recent data for this subreddit"""
    if not os.path.exists('output'):
        return None
    
    # Look for existing files for this subreddit
    pattern = f"reddit_{subreddit_name}_"
    matching_files = []
    
    for filename in os.listdir('output'):
        if filename.startswith(pattern) and filename.endswith('.json'):
            filepath = os.path.join('output', filename)
            # Get file modification time
            mod_time = os.path.getmtime(filepath)
            matching_files.append((filepath, mod_time))
    
    if not matching_files:
        return None
    
    # Get the most recent file
    latest_file = max(matching_files, key=lambda x: x[1])[0]
    
    # Check if it's recent (less than 24 hours old)
    file_age_hours = (time.time() - max(matching_files, key=lambda x: x[1])[1]) / 3600
    
    if file_age_hours < 24:
        return latest_file
    
    return None

def main():
    """Main function - harvest a single subreddit with smart caching"""
    import sys
    
    # Parse arguments
    force_refresh = '--force' in sys.argv or '-f' in sys.argv
    if force_refresh:
        sys.argv = [arg for arg in sys.argv if arg not in ['--force', '-f']]
    
    # Get subreddit name from command line or use default
    if len(sys.argv) > 1:
        subreddit_name = sys.argv[1]
    else:
        subreddit_name = "PersonalFinanceNZ"  # Default
    
    print(f"🚀 REDDIT HARVESTER")
    print(f"📊 Target: r/{subreddit_name}")
    
    if subreddit_name == "PersonalFinanceNZ":
        print("🇳🇿 This community has 124K subscribers discussing financial problems")
        print("💡 Perfect for finding business opportunities in the NZ market!")
    
    # Check for existing data
    if not force_refresh:
        existing_file = check_existing_data(subreddit_name)
        if existing_file:
            print(f"\n💾 Found recent data: {existing_file}")
            file_age_hours = (time.time() - os.path.getmtime(existing_file)) / 3600
            print(f"⏰ Data age: {file_age_hours:.1f} hours")
            
            # Copy to latest_harvest.json for compatibility
            import shutil
            shutil.copy2(existing_file, 'output/latest_harvest.json')
            
            print(f"✅ Using existing data (add --force to refresh)")
            print(f"💡 Run 'python3 analyze_problems.py' to analyze this data")
            return 0
    
    print("=" * 60)
    
    try:
        harvester = RedditHarvester()
        
        # Harvest the subreddit
        data = harvester.harvest_subreddit(subreddit_name, max_posts=800)
        harvester.all_data = data
        
        # Save data
        filename = harvester.save_data(subreddit_name)
        
        # Print stats
        stats = harvester.get_stats()
        print(f"\n📈 HARVEST COMPLETE!")
        print(f"   📑 Posts: {stats['total_posts']:,}")
        print(f"   💬 Comments: {stats['total_comments']:,}")
        print(f"   📊 Total text pieces: {stats['total_text_pieces']:,}")
        print(f"   📅 Date span: {stats['date_range']['span_days']} days")
        print(f"   💾 Saved to: {filename}")
        
        if subreddit_name == "PersonalFinanceNZ":
            print(f"\n💡 This data contains financial problems that could be business opportunities!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
