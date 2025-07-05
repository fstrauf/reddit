#!/usr/bin/env python3
"""
Enhanced Reddit Data Harvester with Delta Fetching
Combines the original harvester with efficient delta updates for large-scale data collection
"""

import os
import json
import sqlite3
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import praw
from dotenv import load_dotenv
from dataclasses import dataclass
from contextlib import contextmanager

# Load environment variables
load_dotenv('../.env.local')

@dataclass
class HarvestCheckpoint:
    """Track harvesting progress for each subreddit"""
    subreddit: str
    last_post_id: Optional[str]
    last_comment_id: Optional[str] 
    last_harvest_time: datetime
    posts_harvested: int
    comments_harvested: int

class RedditDatabase:
    """Database handler for Reddit data storage"""
    
    def __init__(self, db_path: str = "output/reddit_data.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Subreddits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subreddits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    subscribers INTEGER,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reddit_id TEXT UNIQUE NOT NULL,
                    subreddit_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    selftext TEXT,
                    author TEXT,
                    score INTEGER DEFAULT 0,
                    upvote_ratio REAL,
                    num_comments INTEGER DEFAULT 0,
                    created_utc INTEGER,
                    url TEXT,
                    permalink TEXT,
                    sort_method TEXT,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    harvested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subreddit_id) REFERENCES subreddits(id)
                )
            """)
            
            # Comments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reddit_id TEXT UNIQUE NOT NULL,
                    post_id INTEGER NOT NULL,
                    parent_id TEXT,
                    author TEXT,
                    body TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    created_utc INTEGER,
                    depth INTEGER DEFAULT 0,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    harvested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                )
            """)
            
            # Harvest checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS harvest_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subreddit_id INTEGER UNIQUE NOT NULL,
                    last_post_id TEXT,
                    last_comment_id TEXT,
                    last_harvest_time TIMESTAMP,
                    total_posts_harvested INTEGER DEFAULT 0,
                    total_comments_harvested INTEGER DEFAULT 0,
                    harvest_mode TEXT DEFAULT 'full',
                    FOREIGN KEY (subreddit_id) REFERENCES subreddits(id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_reddit_id ON posts(reddit_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_reddit_id ON comments(reddit_id)")
    
    def get_or_create_subreddit(self, name: str, display_name: str = None, 
                               subscribers: int = None, description: str = None) -> int:
        """Get or create a subreddit record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Try to get existing
            cursor.execute("SELECT id FROM subreddits WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            if result:
                # Update if we have new info
                if display_name or subscribers or description:
                    cursor.execute("""
                        UPDATE subreddits 
                        SET display_name = COALESCE(?, display_name),
                            subscribers = COALESCE(?, subscribers),
                            description = COALESCE(?, description),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE name = ?
                    """, (display_name, subscribers, description, name))
                return result['id']
            else:
                # Create new
                cursor.execute("""
                    INSERT INTO subreddits (name, display_name, subscribers, description)
                    VALUES (?, ?, ?, ?)
                """, (name, display_name or name, subscribers, description))
                return cursor.lastrowid
    
    def get_checkpoint(self, subreddit_id: int) -> Optional[HarvestCheckpoint]:
        """Get the last harvest checkpoint for a subreddit"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.name, c.* 
                FROM harvest_checkpoints c
                JOIN subreddits s ON c.subreddit_id = s.id
                WHERE c.subreddit_id = ?
            """, (subreddit_id,))
            
            row = cursor.fetchone()
            if row:
                return HarvestCheckpoint(
                    subreddit=row['name'],
                    last_post_id=row['last_post_id'],
                    last_comment_id=row['last_comment_id'],
                    last_harvest_time=datetime.fromisoformat(row['last_harvest_time']) if row['last_harvest_time'] else None,
                    posts_harvested=row['total_posts_harvested'],
                    comments_harvested=row['total_comments_harvested']
                )
            return None
    
    def update_checkpoint(self, subreddit_id: int, last_post_id: str = None, 
                         last_comment_id: str = None, posts_added: int = 0, 
                         comments_added: int = 0, harvest_mode: str = 'delta'):
        """Update harvest checkpoint"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM harvest_checkpoints WHERE subreddit_id = ?", (subreddit_id,))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute("""
                    UPDATE harvest_checkpoints
                    SET last_post_id = COALESCE(?, last_post_id),
                        last_comment_id = COALESCE(?, last_comment_id),
                        last_harvest_time = CURRENT_TIMESTAMP,
                        total_posts_harvested = total_posts_harvested + ?,
                        total_comments_harvested = total_comments_harvested + ?,
                        harvest_mode = ?
                    WHERE subreddit_id = ?
                """, (last_post_id, last_comment_id, posts_added, comments_added, harvest_mode, subreddit_id))
            else:
                cursor.execute("""
                    INSERT INTO harvest_checkpoints 
                    (subreddit_id, last_post_id, last_comment_id, last_harvest_time, 
                     total_posts_harvested, total_comments_harvested, harvest_mode)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                """, (subreddit_id, last_post_id, last_comment_id, posts_added, comments_added, harvest_mode))
    
    def insert_post(self, post_data: Dict, subreddit_id: int) -> Optional[int]:
        """Insert or update a post"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO posts 
                    (reddit_id, subreddit_id, title, selftext, author, score, 
                     upvote_ratio, num_comments, created_utc, url, permalink, sort_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post_data['id'],
                    subreddit_id,
                    post_data['title'],
                    post_data.get('selftext', ''),
                    post_data.get('author', '[deleted]'),
                    post_data.get('score', 0),
                    post_data.get('upvote_ratio'),
                    post_data.get('num_comments', 0),
                    post_data.get('created_utc'),
                    post_data.get('url'),
                    post_data.get('permalink'),
                    post_data.get('sort_method', 'unknown')
                ))
                
                cursor.execute("SELECT id FROM posts WHERE reddit_id = ?", (post_data['id'],))
                return cursor.fetchone()['id']
                
            except sqlite3.IntegrityError:
                cursor.execute("""
                    UPDATE posts 
                    SET score = ?, num_comments = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE reddit_id = ?
                """, (post_data.get('score', 0), post_data.get('num_comments', 0), post_data['id']))
                
                cursor.execute("SELECT id FROM posts WHERE reddit_id = ?", (post_data['id'],))
                return cursor.fetchone()['id']
    
    def insert_comment(self, comment_data: Dict, post_id: int) -> Optional[int]:
        """Insert or update a comment"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO comments
                    (reddit_id, post_id, parent_id, author, body, score, 
                     created_utc, depth)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    comment_data['id'],
                    post_id,
                    comment_data.get('parent_id'),
                    comment_data.get('author', '[deleted]'),
                    comment_data['text'],
                    comment_data.get('score', 0),
                    comment_data.get('created_utc'),
                    comment_data.get('depth', 0)
                ))
                return cursor.lastrowid
                
            except sqlite3.IntegrityError:
                cursor.execute("""
                    UPDATE comments 
                    SET score = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE reddit_id = ?
                """, (comment_data.get('score', 0), comment_data['id']))
                return None
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) as count FROM subreddits")
            stats['total_subreddits'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM posts")
            stats['total_posts'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM comments")
            stats['total_comments'] = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT s.name, 
                       COUNT(DISTINCT p.id) as post_count,
                       COUNT(DISTINCT c.id) as comment_count,
                       MAX(p.created_utc) as last_post_time,
                       hc.last_harvest_time,
                       hc.harvest_mode
                FROM subreddits s
                LEFT JOIN posts p ON s.id = p.subreddit_id
                LEFT JOIN comments c ON p.id = c.post_id
                LEFT JOIN harvest_checkpoints hc ON s.id = hc.subreddit_id
                GROUP BY s.id
            """)
            
            stats['subreddit_breakdown'] = [dict(row) for row in cursor.fetchall()]
            
            return stats


class EnhancedRedditHarvester:
    """Enhanced Reddit harvester with delta fetching and original functionality"""
    
    def __init__(self, config_file: str = 'config.json', use_database: bool = True):
        self.reddit = self._setup_reddit()
        self.all_data = []  # For backward compatibility
        self.config = self._load_config(config_file)
        self.subreddit_stats = {}
        self.nz_data = self._load_nz_data()
        self.use_database = use_database
        
        # Initialize database if enabled
        if use_database:
            self.db = RedditDatabase()
        else:
            self.db = None
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Add delta configuration if not present
            if 'delta' not in config:
                config['delta'] = {
                    'enabled_subreddits': [],  # Subreddits to use delta for
                    'full_harvest_subreddits': [],  # Subreddits to always full harvest
                    'delta_max_posts': 100,  # Max posts for delta harvests
                    'full_max_posts': 500   # Max posts for full harvests
                }
            
            return config
        except FileNotFoundError:
            print(f"⚠️  Config file {config_file} not found, using defaults")
            return {
                'subreddits': {
                    'default_subreddits': ['PersonalFinanceNZ'],
                    'max_posts_per_subreddit': 200,
                    'preset_groups': {},
                    'validation': {'check_subreddit_exists': True}
                },
                'delta': {
                    'enabled_subreddits': ['PersonalFinanceNZ'],
                    'full_harvest_subreddits': [],
                    'delta_max_posts': 100,
                    'full_max_posts': 500
                }
            }
    
    def _setup_reddit(self) -> praw.Reddit:
        """Initialize Reddit API connection"""
        client_id = os.getenv('NUXT_REDDIT_CLIENT_ID')
        client_secret = os.getenv('NUXT_REDDIT_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Reddit API credentials not found in environment variables")
        
        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="EnhancedRedditHarvester/3.0"
        )
    
    def _load_nz_data(self) -> Dict:
        """Load NZ subreddit data for enhanced validation and insights"""
        try:
            with open('subreddits_nz.json', 'r') as f:
                data = json.load(f)
            return data.get('nz_subreddits', {})
        except FileNotFoundError:
            print("ℹ️  NZ subreddit data file not found (subreddits_nz.json)")
            return {}
    
    def should_use_delta(self, subreddit_name: str) -> bool:
        """Determine if a subreddit should use delta harvesting"""
        delta_config = self.config.get('delta', {})
        
        # Check if explicitly set for full harvest (override delta default)
        if subreddit_name in delta_config.get('full_harvest_subreddits', []):
            return False
        
        # Check if explicitly set for delta
        if subreddit_name in delta_config.get('enabled_subreddits', []):
            return True
        
        # NEW DEFAULT: Always prefer delta if database is enabled
        # This provides much better UX - fast, resumable, no duplicates
        if self.use_database:
            # Check if we have any existing data for this subreddit
            subreddit_id = self.db.get_or_create_subreddit(subreddit_name)
            checkpoint = self.db.get_checkpoint(subreddit_id)
            
            # If no checkpoint exists, this is first harvest - but still use delta!
            # Delta with no checkpoint will harvest recent posts efficiently
            return True
        
        # Fall back to full harvest only if database is disabled
        return False
    
    def harvest_subreddit_delta(self, subreddit_name: str, max_posts: int = None) -> Dict[str, Any]:
        """
        Harvest only new content from a subreddit since last checkpoint
        """
        if not self.use_database:
            raise ValueError("Delta harvesting requires database mode")
        
        if max_posts is None:
            max_posts = self.config.get('delta', {}).get('delta_max_posts', 200)
        
        print(f"\n📊 Smart harvesting r/{subreddit_name}")
        
        # Get or create subreddit
        subreddit = self.reddit.subreddit(subreddit_name)
        subreddit_id = self.db.get_or_create_subreddit(
            subreddit_name,
            subreddit.display_name,
            subreddit.subscribers,
            subreddit.description[:500] if subreddit.description else None
        )
        
        # Get checkpoint
        checkpoint = self.db.get_checkpoint(subreddit_id)
        
        is_first_harvest = not checkpoint or not checkpoint.last_harvest_time
        
        if is_first_harvest:
            print(f"  🆕 First time harvesting - collecting recent posts efficiently")
            print(f"  📊 Will fetch up to {max_posts} recent posts")
        else:
            print(f"  🔄 Delta update since {checkpoint.last_harvest_time}")
            print(f"  📊 Previously: {checkpoint.posts_harvested} posts, {checkpoint.comments_harvested} comments")
        
        # Track new content
        new_posts = 0
        new_comments = 0
        latest_post_id = None
        posts_processed = 0
        
        print(f"  📥 Fetching recent posts...")
        
        # Fetch posts from 'new' to get the latest content
        try:
            for i, submission in enumerate(subreddit.new(limit=max_posts), 1):
                # Check if we've seen this post before (for subsequent harvests)
                if checkpoint and checkpoint.last_post_id == submission.id:
                    print(f"  ✅ Reached last checkpoint at post {submission.id} (after {i} posts)")
                    break
                
                # Store the latest post ID (first post we see)
                if not latest_post_id:
                    latest_post_id = submission.id
                
                # Process post
                post_data = {
                    'id': submission.id,
                    'title': submission.title,
                    'selftext': submission.selftext,
                    'score': submission.score,
                    'upvote_ratio': submission.upvote_ratio,
                    'num_comments': submission.num_comments,
                    'created_utc': int(submission.created_utc),
                    'url': submission.url,
                    'permalink': submission.permalink,
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'sort_method': 'new_delta'
                }
                
                post_id = self.db.insert_post(post_data, subreddit_id)
                if post_id:
                    new_posts += 1
                    
                    # Harvest comments efficiently
                    submission.comments.replace_more(limit=0)  # Don't load "more comments"
                    comment_count = 0
                    for comment in submission.comments.list():
                        if hasattr(comment, 'body') and comment.body not in ['[deleted]', '[removed]']:
                            comment_data = {
                                'id': comment.id,
                                'text': comment.body,
                                'score': comment.score,
                                'created_utc': int(comment.created_utc),
                                'author': str(comment.author) if comment.author else '[deleted]',
                                'parent_id': comment.parent_id,
                                'depth': comment.depth if hasattr(comment, 'depth') else 0
                            }
                            
                            if self.db.insert_comment(comment_data, post_id):
                                new_comments += 1
                                comment_count += 1
                
                posts_processed += 1
                
                # Progress indicator every 25 posts
                if posts_processed % 25 == 0:
                    print(f"    � Processed {posts_processed} posts, found {new_posts} new...")
                    
        except Exception as e:
            print(f"    ⚠️  Error during harvest: {e}")
        
        # Update checkpoint
        if latest_post_id:
            self.db.update_checkpoint(
                subreddit_id, 
                last_post_id=latest_post_id,
                posts_added=new_posts,
                comments_added=new_comments,
                harvest_mode='delta'
            )
        
        # Success message
        if is_first_harvest:
            print(f"  🎉 Initial harvest complete: {new_posts} posts, {new_comments} comments")
        else:
            if new_posts > 0:
                print(f"  ✅ Delta update complete: +{new_posts} posts, +{new_comments} comments")
            else:
                print(f"  😴 No new content since last harvest")
        
        stats = {
            'subreddit': subreddit_name,
            'harvest_mode': 'delta',
            'new_posts': new_posts,
            'new_comments': new_comments,
            'posts_processed': posts_processed,
            'checkpoint_updated': latest_post_id is not None,
            'was_first_harvest': is_first_harvest
        }
        
        return stats
    
    def harvest_subreddit_full(self, subreddit_name: str, max_posts: int = 500) -> List[Dict]:
        """
        Original full harvest method for backward compatibility and full data collection
        """
        print(f"\n🏗️  Full harvesting r/{subreddit_name}")
        print("=" * 50)
        
        subreddit = self.reddit.subreddit(subreddit_name)
        subreddit_data = []
        
        # If using database, also store there
        subreddit_id = None
        if self.use_database:
            subreddit_id = self.db.get_or_create_subreddit(
                subreddit_name,
                subreddit.display_name,
                subreddit.subscribers,
                subreddit.description[:500] if subreddit.description else None
            )
        
        # Different sorting methods to get maximum coverage
        sorting_methods = [
            ('hot', subreddit.hot(limit=max_posts//4)),
            ('new', subreddit.new(limit=max_posts//4)), 
            ('top_year', subreddit.top(time_filter='year', limit=max_posts//4)),
            ('top_all', subreddit.top(time_filter='all', limit=max_posts//4))
        ]
        
        total_posts = 0
        total_comments = 0
        latest_post_id = None
        
        for sort_name, submissions in sorting_methods:
            print(f"  📥 Collecting {sort_name} posts...")
            
            try:
                for submission in submissions:
                    # Skip if we already have this post
                    if any(post['id'] == submission.id for post in subreddit_data):
                        continue
                    
                    # Track latest post for checkpoint
                    if not latest_post_id and sort_name == 'new':
                        latest_post_id = submission.id
                        
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
                    
                    # Collect ALL comments
                    comments = self._harvest_all_comments(submission)
                    post_data['comments'] = comments
                    
                    subreddit_data.append(post_data)
                    total_posts += 1
                    total_comments += len(comments)
                    
                    # Store in database if enabled
                    if self.use_database:
                        db_post_data = post_data.copy()
                        db_post_data['permalink'] = submission.permalink
                        post_id = self.db.insert_post(db_post_data, subreddit_id)
                        
                        if post_id:
                            for comment in comments:
                                self.db.insert_comment(comment, post_id)
                    
                    if len(subreddit_data) % 50 == 0:
                        print(f"    ✅ Collected {len(subreddit_data)} posts so far...")
                        
            except Exception as e:
                print(f"    ⚠️  Error in {sort_name}: {e}")
                continue
        
        # Update checkpoint for full harvest
        if self.use_database and latest_post_id:
            self.db.update_checkpoint(
                subreddit_id,
                last_post_id=latest_post_id,
                posts_added=total_posts,
                comments_added=total_comments,
                harvest_mode='full'
            )
        
        print(f"  🎉 Total collected from r/{subreddit_name}: {len(subreddit_data)} posts")
        return subreddit_data
    
    def _harvest_all_comments(self, submission) -> List[Dict]:
        """Get ALL comments from a submission"""
        comments = []
        
        try:
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
    
    def harvest_multiple_subreddits(self, subreddit_names: List[str], 
                                  max_posts_per_sub: int = None,
                                  force_mode: str = None) -> List[Dict]:
        """
        Harvest multiple subreddits using intelligent mode selection
        
        Args:
            subreddit_names: List of subreddit names
            max_posts_per_sub: Max posts per subreddit 
            force_mode: Force 'delta' or 'full' mode for all subreddits
        """
        print(f"🚀 ENHANCED REDDIT HARVESTER WITH DELTA SUPPORT")
        print(f"📊 Targeting {len(subreddit_names)} subreddits")
        
        if self.use_database:
            print(f"⚡ Smart mode: Delta harvesting enabled (fast & efficient!)")
            print(f"💡 First run: Quick collection of recent posts")
            print(f"💡 Subsequent runs: Lightning-fast delta updates")
        else:
            print(f"📄 JSON-only mode: Traditional full harvesting")
            print(f"💡 Tip: Remove --no-database for much faster incremental updates!")
            
        print("=" * 60)
        
        all_data = []
        all_stats = []
        delta_used_count = 0
        
        for i, subreddit_name in enumerate(subreddit_names, 1):
            print(f"\n📂 [{i}/{len(subreddit_names)}] Processing r/{subreddit_name}")
            
            try:
                # Determine harvest mode
                if force_mode:
                    use_delta = force_mode == 'delta'
                    mode_reason = f"(forced {force_mode})"
                else:
                    use_delta = self.should_use_delta(subreddit_name)
                    if use_delta:
                        delta_used_count += 1
                        # Check if this is first time harvest
                        subreddit_id = self.db.get_or_create_subreddit(subreddit_name)
                        checkpoint = self.db.get_checkpoint(subreddit_id)
                        
                        if checkpoint is None:
                            mode_reason = "(smart delta - first harvest)"
                        else:
                            last_time = checkpoint.last_harvest_time
                            if last_time:
                                time_diff = datetime.now() - last_time
                                if time_diff.days > 0:
                                    mode_reason = f"(smart delta - {time_diff.days} days since last)"
                                else:
                                    hours = time_diff.seconds // 3600
                                    mode_reason = f"(smart delta - {hours}h since last)"
                            else:
                                mode_reason = "(smart delta - resuming)"
                    else:
                        mode_reason = "(full harvest - comprehensive)"
                
                print(f"  🎯 Mode: {'Delta' if use_delta else 'Full'} {mode_reason}")
                
                if use_delta and self.use_database:
                    # Delta harvest - fast and efficient
                    delta_max = max_posts_per_sub or self.config.get('delta', {}).get('delta_max_posts', 200)
                    print(f"  ⚡ Fast delta scan (up to {delta_max} recent posts)")
                    stats = self.harvest_subreddit_delta(subreddit_name, delta_max)
                    all_stats.append(stats)
                    
                    # For backward compatibility, don't add to all_data for delta harvests
                    # Users can access data through database queries
                    
                else:
                    # Full harvest - comprehensive but slower
                    full_max = max_posts_per_sub or self.config.get('delta', {}).get('full_max_posts', 500)
                    print(f"  ⚠️  Full harvest may take 3-5 minutes... (scanning {full_max} posts)")
                    subreddit_data = self.harvest_subreddit_full(subreddit_name, full_max)
                    all_data.extend(subreddit_data)
                    
                    # Track stats
                    self.subreddit_stats[subreddit_name] = {
                        'posts': len(subreddit_data),
                        'comments': sum(len(post['comments']) for post in subreddit_data),
                        'total_text_pieces': len(subreddit_data) + sum(len(post['comments']) for post in subreddit_data),
                        'harvest_mode': 'full'
                    }
                
            except Exception as e:
                print(f"  ❌ Failed to harvest r/{subreddit_name}: {e}")
                continue
        
        # Summary
        if self.use_database:
            db_stats = self.db.get_stats()
            print(f"\n📊 HARVEST SUMMARY")
            print(f"   ⚡ Delta harvests: {delta_used_count}/{len(subreddit_names)}")
            print(f"   💾 Total in database: {db_stats['total_posts']:,} posts, {db_stats['total_comments']:,} comments")
            
            if delta_used_count == len(subreddit_names):
                print(f"\n🎉 All subreddits used fast delta mode!")
                print(f"💡 Next run will be even faster - only new content will be fetched")
            elif delta_used_count > 0:
                print(f"\n✨ {delta_used_count} subreddits used fast delta mode")
                print(f"💡 Full harvests will switch to delta mode after first run")
            
            # Show what to do next
            print(f"\n🔍 NEXT STEPS:")
            print(f"   📊 Check stats: python harvest_reddit_enhanced.py --stats") 
            print(f"   🔄 Run again: python harvest_reddit_enhanced.py {' '.join(subreddit_names)}")
            print(f"   📈 Analyze data: Use database queries or run analysis scripts")
        else:
            print(f"\n📊 HARVEST SUMMARY")
            print(f"   📄 JSON harvest complete")
            print(f"   💡 Consider using database mode for faster incremental updates!")
            
        print("=" * 60)
        
        return all_data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        if self.use_database:
            return self.db.get_stats()
        else:
            # Original stats method for backward compatibility
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
                },
                'per_subreddit_stats': self.subreddit_stats
            }
    
    def save_data(self, subreddit_names: List[str] = None, custom_name: str = None) -> str:
        """Save harvested data to file (for backward compatibility)"""
        if not self.all_data:
            print("ℹ️  No data to save (using database mode or no full harvests performed)")
            return ""
        
        os.makedirs('output', exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if custom_name:
            filename = f'output/reddit_{custom_name}_{timestamp}.json'
        elif subreddit_names and len(subreddit_names) == 1:
            filename = f'output/reddit_{subreddit_names[0]}_{timestamp}.json'
        elif subreddit_names and len(subreddit_names) > 1:
            if len(subreddit_names) <= 3:
                name_part = '_'.join(subreddit_names)
            else:
                name_part = f"{subreddit_names[0]}_and_{len(subreddit_names)-1}_others"
            filename = f'output/reddit_multi_{name_part}_{timestamp}.json'
        else:
            filename = f'output/reddit_harvest_{timestamp}.json'
        
        # Prepare data with metadata
        harvest_data = {
            'metadata': {
                'harvest_timestamp': timestamp,
                'subreddits_harvested': subreddit_names or ['unknown'],
                'total_posts': len(self.all_data),
                'total_comments': sum(len(post['comments']) for post in self.all_data),
                'subreddit_stats': self.subreddit_stats,
                'harvester_version': '3.0'
            },
            'data': self.all_data
        }
        
        # Save main file
        with open(filename, 'w') as f:
            json.dump(harvest_data, f, indent=2)
        
        # Also save as latest (backward compatibility)
        with open('output/latest_harvest.json', 'w') as f:
            json.dump(self.all_data, f, indent=2)
            
        return filename


def main():
    """Enhanced main function with delta support"""
    parser = argparse.ArgumentParser(
        description='Enhanced Reddit Data Harvester with Delta Fetching',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 SMART HARVESTING (DEFAULT): Automatically uses fast delta mode!

Quick Start:
  # Smart harvesting - detects what you need automatically
  python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ
  
  # First run: harvests recent posts efficiently 
  # Subsequent runs: only fetches new content (super fast!)

Examples:
  # Single subreddit (smart mode - RECOMMENDED)
  python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ
  
  # Multiple subreddits 
  python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ entrepreneur startups
  
  # Force full comprehensive harvest (slower, for special cases)
  python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full
  
  # Force delta-only mode 
  python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode delta
  
Database & Stats:
  # Check current data
  python3 harvest_reddit_enhanced.py --stats
  
  # Reset a subreddit to start fresh
  python3 harvest_reddit_enhanced.py --reset-checkpoint PersonalFinanceNZ

🎯 Smart Mode Benefits:
  - First run: Fast collection of recent posts (not slow full scan)
  - Subsequent runs: Lightning fast - only new content
  - Resumable: Interrupted harvests continue where they left off
  - No duplicates: Intelligent deduplication 
  
💡 Performance: Smart mode is 5-10x faster than full harvests!
        """
    )
    
    # Main actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--subreddits', nargs='+',
                             help='Subreddits to harvest')
    action_group.add_argument('--stats', action='store_true',
                             help='Show database statistics')
    action_group.add_argument('--reset-checkpoint', type=str,
                             help='Reset checkpoint for a subreddit')
    
    # Options
    parser.add_argument('--mode', choices=['delta', 'full', 'smart'], default='smart',
                       help='Harvest mode: delta (fast updates), full (comprehensive), smart (intelligent - DEFAULT)')
    parser.add_argument('--posts-per-sub', type=int,
                       help='Maximum posts per subreddit (smart: 200 delta, 500 full)')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Configuration file path')
    parser.add_argument('--no-database', action='store_true',
                       help='Disable database storage (forces JSON-only mode)')
    parser.add_argument('--output-name', type=str,
                       help='Custom name for output file')
    
    args = parser.parse_args()
    
    try:
        # Initialize harvester
        use_db = not args.no_database
        harvester = EnhancedRedditHarvester(args.config, use_database=use_db)
        
        # Handle stats request
        if args.stats:
            if not use_db:
                print("❌ Stats require database mode")
                return 1
                
            stats = harvester.get_stats()
            print("📊 DATABASE STATISTICS")
            print("=" * 40)
            print(f"🗂️  Subreddits: {stats['total_subreddits']}")
            print(f"📑 Posts: {stats['total_posts']:,}")
            print(f"💬 Comments: {stats['total_comments']:,}")
            
            print(f"\n📋 Per-Subreddit Breakdown:")
            for sub_stats in stats['subreddit_breakdown']:
                name = sub_stats['name']
                posts = sub_stats['post_count']
                comments = sub_stats['comment_count']
                last_harvest = sub_stats.get('last_harvest_time', 'Never')
                mode = sub_stats.get('harvest_mode', 'Unknown')
                
                print(f"  r/{name}: {posts} posts, {comments} comments | Last: {last_harvest} ({mode})")
            
            return 0
        
        # Handle checkpoint reset
        if args.reset_checkpoint:
            if not use_db:
                print("❌ Checkpoint reset requires database mode")
                return 1
                
            subreddit_id = harvester.db.get_or_create_subreddit(args.reset_checkpoint)
            with harvester.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM harvest_checkpoints WHERE subreddit_id = ?", (subreddit_id,))
                print(f"✅ Reset checkpoint for r/{args.reset_checkpoint}")
            return 0
        
        # Default to config defaults if no subreddits specified
        if not args.subreddits:
            default_subreddits = harvester.config.get('subreddits', {}).get('default_subreddits', ['PersonalFinanceNZ'])
            args.subreddits = default_subreddits
            print(f"📋 Using default subreddits: {', '.join(args.subreddits)}")
        
        # Harvest data
        force_mode = args.mode if args.mode != 'smart' else None
        all_data = harvester.harvest_multiple_subreddits(
            args.subreddits, 
            args.posts_per_sub,
            force_mode
        )
        
        harvester.all_data = all_data
        
        # Save data if we have any (full harvests)
        if all_data:
            filename = harvester.save_data(args.subreddits, args.output_name)
            print(f"\n💾 Data saved to: {filename}")
        
        # Print stats
        stats = harvester.get_stats()
        if 'error' not in stats:
            if use_db:
                print(f"\n📈 CURRENT DATABASE STATE:")
                print(f"   📑 Total Posts: {stats['total_posts']:,}")
                print(f"   💬 Total Comments: {stats['total_comments']:,}")
            else:
                print(f"\n📈 HARVEST COMPLETE!")
                print(f"   📑 Posts: {stats['total_posts']:,}")
                print(f"   💬 Comments: {stats['total_comments']:,}")
        
        # Final guidance
        if use_db:
            print(f"\n🎯 NEXT STEPS:")
            print(f"   📊 Check progress: python harvest_reddit_enhanced.py --stats")
            print(f"   � Run again for updates: python harvest_reddit_enhanced.py --subreddits {' '.join(args.subreddits)}")
            print(f"   📈 Analyze data: python run_analysis.py analyze")
            print(f"\n💡 Tip: Run regularly for automatic delta updates - they're super fast!")
        else:
            print(f"\n💡 Consider using database mode (default) for much faster incremental updates!")
        
        
    except KeyboardInterrupt:
        print("\n⚠️  Harvest interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
