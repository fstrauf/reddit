#!/usr/bin/env python3
"""
Enhanced Reddit Data Harvester - Flexible multi-subreddit data collection
Supports multiple subreddits, preset groups, validation, and smart management
"""

import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import praw
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env.local')

class EnhancedRedditHarvester:
    """Enhanced Reddit data harvester with multi-subreddit support"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.reddit = self._setup_reddit()
        self.all_data = []
        self.config = self._load_config(config_file)
        self.subreddit_stats = {}
        self.nz_data = self._load_nz_data()
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Config file {config_file} not found, using defaults")
            return {
                'subreddits': {
                    'default_subreddits': ['PersonalFinanceNZ'],
                    'max_posts_per_subreddit': 200,
                    'preset_groups': {},
                    'validation': {'check_subreddit_exists': True}
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
            user_agent="EnhancedRedditHarvester/2.0"
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
    
    def get_nz_subreddit_info(self, subreddit_name: str) -> Optional[Dict]:
        """Get NZ-specific subreddit information if available"""
        if not self.nz_data:
            return None
        
        # Search through all categories for the subreddit
        for category_name, category_data in self.nz_data.get('categories', {}).items():
            if isinstance(category_data, list):
                for sub_info in category_data:
                    if sub_info.get('name') == subreddit_name:
                        sub_info['category'] = category_name
                        return sub_info
        
        # Also check tiers
        for tier_name, tier_data in self.nz_data.get('tiers', {}).items():
            if 'subreddits' in tier_data:
                for sub_info in tier_data['subreddits']:
                    if sub_info.get('name') == subreddit_name:
                        sub_info['tier'] = tier_name
                        return sub_info
        
        return None
    
    def get_nz_business_strategy(self, subreddit_name: str) -> Optional[Dict]:
        """Get business strategy recommendations for NZ subreddits"""
        if not self.nz_data:
            return None
            
        strategy_data = self.nz_data.get('business_discovery_strategy', {})
        
        # Check primary targets
        for target in strategy_data.get('primary_targets', []):
            if target.get('subreddit') == subreddit_name:
                return {
                    'priority': target.get('priority'),
                    'reasons': target.get('reasons', []),
                    'approach': target.get('approach'),
                    'type': 'primary'
                }
        
        # Check secondary targets
        for target in strategy_data.get('secondary_targets', []):
            if target.get('subreddit') == subreddit_name:
                return {
                    'priority': target.get('priority'),
                    'reasons': target.get('reasons', []),
                    'approach': target.get('approach'),
                    'type': 'secondary'
                }
        
        return None
    
    def validate_subreddit(self, subreddit_name: str) -> Dict[str, Any]:
        """Validate if a subreddit exists and get basic info"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Try to access subreddit properties to check if it exists
            subscriber_count = subreddit.subscribers
            display_name = subreddit.display_name
            description = subreddit.description
            
            # Check if it's private/banned
            if subscriber_count is None:
                return {'valid': False, 'reason': 'Private or banned subreddit'}
            
            # Check minimum subscriber count
            min_subscribers = self.config['subreddits']['validation'].get('min_subscriber_count', 1000)
            if subscriber_count < min_subscribers:
                return {
                    'valid': True,
                    'warning': f'Low subscriber count: {subscriber_count:,} (minimum recommended: {min_subscribers:,})',
                    'subscribers': subscriber_count,
                    'display_name': display_name
                }
            
            validation_result = {
                'valid': True,
                'subscribers': subscriber_count,
                'display_name': display_name,
                'description': description[:200] + '...' if len(description) > 200 else description
            }
            
            # Add NZ-specific insights if available
            nz_info = self.get_nz_subreddit_info(subreddit_name)
            nz_strategy = self.get_nz_business_strategy(subreddit_name)
            
            if nz_info:
                validation_result['nz_info'] = {
                    'business_relevance': nz_info.get('business_relevance'),
                    'category': nz_info.get('category'),
                    'tier': nz_info.get('tier'),
                    'target_audience': nz_info.get('target_audience'),
                    'pain_points': nz_info.get('pain_points', [])
                }
                
            if nz_strategy:
                validation_result['nz_strategy'] = nz_strategy
            
            return validation_result
            
        except Exception as e:
            return {'valid': False, 'reason': f'Subreddit not found or inaccessible: {e}'}
    
    def get_preset_subreddits(self, group_name: str) -> List[str]:
        """Get subreddits from a preset group"""
        preset_groups = self.config['subreddits'].get('preset_groups', {})
        
        if group_name not in preset_groups:
            available_groups = list(preset_groups.keys())
            raise ValueError(f"Unknown preset group '{group_name}'. Available groups: {available_groups}")
        
        return preset_groups[group_name]
    
    def list_preset_groups(self) -> Dict[str, List[str]]:
        """List all available preset groups"""
        return self.config['subreddits'].get('preset_groups', {})
    
    def expand_subreddit_inputs(self, inputs: List[str]) -> List[str]:
        """Expand subreddit inputs (handle preset groups and individual subreddits)"""
        expanded = []
        preset_groups = self.config['subreddits'].get('preset_groups', {})
        
        for input_item in inputs:
            if input_item.startswith('group:'):
                # Handle preset group
                group_name = input_item[6:]  # Remove 'group:' prefix
                if group_name in preset_groups:
                    group_subreddits = preset_groups[group_name]
                    expanded.extend(group_subreddits)
                    print(f"📦 Expanded group '{group_name}': {', '.join(group_subreddits)}")
                else:
                    print(f"⚠️  Unknown preset group: {group_name}")
            else:
                # Handle individual subreddit
                expanded.append(input_item)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_expanded = []
        for sub in expanded:
            if sub not in seen:
                seen.add(sub)
                unique_expanded.append(sub)
        
        return unique_expanded
    
    def harvest_multiple_subreddits(self, subreddit_names: List[str], max_posts_per_sub: int = None) -> List[Dict]:
        """Harvest data from multiple subreddits"""
        if max_posts_per_sub is None:
            max_posts_per_sub = self.config['subreddits'].get('max_posts_per_subreddit', 200)
        
        print(f"🚀 ENHANCED REDDIT HARVESTER")
        print(f"📊 Targeting {len(subreddit_names)} subreddits")
        print(f"📈 Max posts per subreddit: {max_posts_per_sub}")
        print("=" * 60)
        
        all_data = []
        failed_subreddits = []
        
        # Validate subreddits first if enabled
        if self.config['subreddits']['validation'].get('check_subreddit_exists', True):
            print("🔍 Validating subreddits...")
            validated_subreddits = []
            
            for subreddit_name in subreddit_names:
                validation_result = self.validate_subreddit(subreddit_name)
                
                if validation_result['valid']:
                    validated_subreddits.append(subreddit_name)
                    if 'warning' in validation_result:
                        print(f"  ⚠️  r/{subreddit_name}: {validation_result['warning']}")
                    else:
                        subs = validation_result.get('subscribers', 'Unknown')
                        base_msg = f"  ✅ r/{subreddit_name}: {subs:,} subscribers"
                        
                        # Add NZ-specific insights
                        if 'nz_info' in validation_result:
                            nz_info = validation_result['nz_info']
                            base_msg += f" | {nz_info.get('business_relevance', 'unknown').title()} Business Relevance"
                            if nz_info.get('category'):
                                base_msg += f" | {nz_info['category'].replace('_', ' ').title()}"
                                
                        if 'nz_strategy' in validation_result:
                            nz_strategy = validation_result['nz_strategy']
                            priority = nz_strategy.get('priority', '').replace('_', ' ').title()
                            target_type = nz_strategy.get('type', '').title()
                            base_msg += f" | 🎯 {target_type} Target ({priority} Priority)"
                            
                        print(base_msg)
                else:
                    print(f"  ❌ r/{subreddit_name}: {validation_result['reason']}")
                    failed_subreddits.append(subreddit_name)
            
            subreddit_names = validated_subreddits
            
            if not subreddit_names:
                print("❌ No valid subreddits to harvest!")
                return []
        
        # Harvest each subreddit
        for i, subreddit_name in enumerate(subreddit_names, 1):
            print(f"\n📂 [{i}/{len(subreddit_names)}] Harvesting r/{subreddit_name}")
            
            try:
                subreddit_data = self.harvest_subreddit(subreddit_name, max_posts_per_sub)
                all_data.extend(subreddit_data)
                
                # Track stats per subreddit
                self.subreddit_stats[subreddit_name] = {
                    'posts': len(subreddit_data),
                    'comments': sum(len(post['comments']) for post in subreddit_data),
                    'total_text_pieces': len(subreddit_data) + sum(len(post['comments']) for post in subreddit_data)
                }
                
            except Exception as e:
                print(f"  ❌ Failed to harvest r/{subreddit_name}: {e}")
                failed_subreddits.append(subreddit_name)
                continue
        
        # Summary
        print(f"\n📊 HARVEST SUMMARY")
        print(f"✅ Successfully harvested: {len(subreddit_names) - len(failed_subreddits)} subreddits")
        if failed_subreddits:
            print(f"❌ Failed subreddits: {', '.join(failed_subreddits)}")
        
        return all_data
    
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
    
    def save_data(self, subreddit_names: List[str] = None, custom_name: str = None) -> str:
        """Save harvested data to file with enhanced naming"""
        os.makedirs('output', exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if custom_name:
            filename = f'output/reddit_{custom_name}_{timestamp}.json'
        elif subreddit_names and len(subreddit_names) == 1:
            filename = f'output/reddit_{subreddit_names[0]}_{timestamp}.json'
        elif subreddit_names and len(subreddit_names) > 1:
            # Multi-subreddit filename
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
                'harvester_version': '2.0'
            },
            'data': self.all_data
        }
        
        # Save main file
        with open(filename, 'w') as f:
            json.dump(harvest_data, f, indent=2)
        
        # Also save as latest (backward compatibility)
        with open('output/latest_harvest.json', 'w') as f:
            json.dump(self.all_data, f, indent=2)  # Keep old format for compatibility
            
        return filename
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the harvested data"""
        if not self.all_data:
            return {"error": "No data harvested yet"}
        
        total_posts = len(self.all_data)
        total_comments = sum(len(post['comments']) for post in self.all_data)
        
        # Calculate date range
        timestamps = [post['created_utc'] for post in self.all_data]
        oldest = datetime.fromtimestamp(min(timestamps))
        newest = datetime.fromtimestamp(max(timestamps))
        
        # Subreddit breakdown
        subreddit_breakdown = {}
        for post in self.all_data:
            subreddit = post['subreddit']
            if subreddit not in subreddit_breakdown:
                subreddit_breakdown[subreddit] = {'posts': 0, 'comments': 0}
            subreddit_breakdown[subreddit]['posts'] += 1
            subreddit_breakdown[subreddit]['comments'] += len(post['comments'])
        
        # Top authors
        author_counts = {}
        for post in self.all_data:
            author = post.get('author', '[deleted]')
            author_counts[author] = author_counts.get(author, 0) + 1
            for comment in post['comments']:
                comment_author = comment.get('author', '[deleted]')
                author_counts[comment_author] = author_counts.get(comment_author, 0) + 1
        
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_posts': total_posts,
            'total_comments': total_comments,
            'total_text_pieces': total_posts + total_comments,
            'subreddits_harvested': len(subreddit_breakdown),
            'subreddit_breakdown': subreddit_breakdown,
            'top_authors': top_authors,
            'date_range': {
                'oldest': oldest.strftime('%Y-%m-%d'),
                'newest': newest.strftime('%Y-%m-%d'),
                'span_days': (newest - oldest).days
            },
            'per_subreddit_stats': self.subreddit_stats
        }

def list_preset_groups(config_file: str = 'config.json') -> None:
    """List all available preset groups"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        preset_groups = config.get('subreddits', {}).get('preset_groups', {})
    except FileNotFoundError:
        print(f"⚠️  Config file {config_file} not found")
        return
    
    if not preset_groups:
        print("❌ No preset groups found in configuration")
        return
    
    # Separate NZ and general groups
    nz_groups = {k: v for k, v in preset_groups.items() if k.startswith('nz_')}
    general_groups = {k: v for k, v in preset_groups.items() if not k.startswith('nz_')}
    
    print("📦 AVAILABLE PRESET GROUPS")
    print("=" * 50)
    
    if general_groups:
        print("\n🌍 GENERAL GROUPS:")
        for group_name, subreddits in general_groups.items():
            print(f"  🏷️  group:{group_name}")
            print(f"     📊 {len(subreddits)} subreddits: {', '.join(subreddits)}")
    
    if nz_groups:
        print("\n🥝 NEW ZEALAND GROUPS:")
        for group_name, subreddits in nz_groups.items():
            print(f"  🏷️  group:{group_name}")
            print(f"     📊 {len(subreddits)} subreddits: {', '.join(subreddits)}")
        
        print("\n💡 NZ Strategic Groups:")
        print("   🎯 nz_primary_targets   - High-value business discovery targets")
        print("   🎯 nz_finance          - Financial problem discovery focus")
        print("   🎯 nz_local_advantage  - Leverage your Tauranga location")
        print("   🎯 nz_tier1            - Major NZ communities (massive reach)")
    
    print(f"\n💡 Usage: --subreddits group:nz_finance group:tech entrepreneur")
    print(f"💡 Mix individual subreddits with groups: --subreddits group:nz_business productivity")

def validate_subreddits_only(subreddit_names: List[str], config_file: str = 'config.json') -> None:
    """Validate subreddits without harvesting"""
    print("🔍 SUBREDDIT VALIDATION")
    print("=" * 40)
    
    try:
        harvester = EnhancedRedditHarvester(config_file)
        
        for subreddit_name in subreddit_names:
            print(f"\n📍 Checking r/{subreddit_name}...")
            result = harvester.validate_subreddit(subreddit_name)
            
            if result['valid']:
                if 'warning' in result:
                    print(f"  ⚠️  {result['warning']}")
                else:
                    print(f"  ✅ Valid subreddit")
                    print(f"     Subscribers: {result.get('subscribers', 'Unknown'):,}")
                    if 'description' in result:
                        print(f"     Description: {result['description']}")
                    
                    # Show NZ-specific insights
                    if 'nz_info' in result:
                        nz_info = result['nz_info']
                        print(f"     🥝 NZ Context:")
                        print(f"        Business Relevance: {nz_info.get('business_relevance', 'unknown').title()}")
                        if nz_info.get('category'):
                            print(f"        Category: {nz_info['category'].replace('_', ' ').title()}")
                        if nz_info.get('target_audience'):
                            print(f"        Target Audience: {nz_info['target_audience'].replace('_', ' ').title()}")
                        if nz_info.get('pain_points'):
                            print(f"        Pain Points: {', '.join(nz_info['pain_points'])}")
                    
                    if 'nz_strategy' in result:
                        nz_strategy = result['nz_strategy']
                        print(f"     🎯 Business Strategy:")
                        print(f"        Priority: {nz_strategy.get('priority', '').replace('_', ' ').title()}")
                        print(f"        Target Type: {nz_strategy.get('type', '').title()}")
                        print(f"        Approach: {nz_strategy.get('approach', '').replace('_', ' ').title()}")
                        if nz_strategy.get('reasons'):
                            print(f"        Reasons: {', '.join(nz_strategy['reasons'])}")
            else:
                print(f"  ❌ {result['reason']}")
                
    except Exception as e:
        print(f"❌ Error during validation: {e}")

def show_nz_strategy(config_file: str = 'config.json') -> None:
    """Show NZ market penetration strategy"""
    harvester = EnhancedRedditHarvester(config_file)
    
    if not harvester.nz_data:
        print("❌ NZ subreddit data not available")
        return
    
    print("🥝 NEW ZEALAND MARKET STRATEGY")
    print("=" * 50)
    
    strategy_data = harvester.nz_data.get('business_discovery_strategy', {})
    
    # Primary targets
    primary_targets = strategy_data.get('primary_targets', [])
    if primary_targets:
        print("\n🎯 PRIMARY TARGETS (Start Here):")
        for target in primary_targets:
            subreddit = target.get('subreddit')
            subscribers = target.get('subscribers', 'Unknown')
            priority = target.get('priority', '').replace('_', ' ').title()
            approach = target.get('approach', '').replace('_', ' ').title()
            reasons = target.get('reasons', [])
            
            print(f"  📍 r/{subreddit}")
            print(f"     👥 {subscribers:,} subscribers | 🎯 {priority} Priority")
            print(f"     📈 Strategy: {approach}")
            print(f"     💡 Why: {', '.join(reasons)}")
    
    # Secondary targets
    secondary_targets = strategy_data.get('secondary_targets', [])
    if secondary_targets:
        print("\n🎯 SECONDARY TARGETS (Expand Later):")
        for target in secondary_targets:
            subreddit = target.get('subreddit')
            subscribers = target.get('subscribers', 'Unknown')
            priority = target.get('priority', '').replace('_', ' ').title()
            approach = target.get('approach', '').replace('_', ' ').title()
            reasons = target.get('reasons', [])
            
            print(f"  📍 r/{subreddit}")
            print(f"     👥 {subscribers:,} subscribers | 🎯 {priority} Priority")
            print(f"     📈 Strategy: {approach}")
            print(f"     💡 Why: {', '.join(reasons)}")
    
    # Implementation phases
    phases = harvester.nz_data.get('implementation_phases', {})
    if phases:
        print(f"\n📅 IMPLEMENTATION PHASES:")
        for phase_name, phase_data in phases.items():
            duration = phase_data.get('duration', 'Unknown')
            focus = phase_data.get('focus', 'Unknown')
            targets = phase_data.get('target_subreddits', [])
            
            print(f"  📋 {phase_name.replace('_', ' ').title()}")
            print(f"     ⏱️  Duration: {duration}")
            print(f"     🎯 Focus: {focus}")
            print(f"     📍 Targets: {', '.join(targets)}")
    
    print(f"\n💡 Quick Start Commands:")
    print(f"   🚀 Start with primary targets: --subreddits group:nz_primary_targets")
    print(f"   🎯 Focus on finance: --subreddits group:nz_finance")
    print(f"   🏠 Local advantage: --subreddits group:nz_local_advantage")

def main():
    """Enhanced main function with comprehensive CLI support"""
    parser = argparse.ArgumentParser(
        description='Enhanced Reddit Data Harvester - Multi-subreddit support with preset groups',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single subreddit
  python3 harvest_reddit.py --subreddits PersonalFinanceNZ
  
  # Multiple subreddits
  python3 harvest_reddit.py --subreddits entrepreneur startups programming
  
  # Use preset group
  python3 harvest_reddit.py --subreddits group:finance
  
  # NZ-specific strategic groups
  python3 harvest_reddit.py --subreddits group:nz_primary_targets
  python3 harvest_reddit.py --subreddits group:nz_finance
  python3 harvest_reddit.py --subreddits group:nz_local_advantage
  
  # Mix preset groups and individual subreddits
  python3 harvest_reddit.py --subreddits group:nz_business tauranga
  
  # Show all available preset groups (including NZ groups)
  python3 harvest_reddit.py --list-groups
  
  # Show NZ market penetration strategy
  python3 harvest_reddit.py --nz-strategy
  
  # Validate subreddits with NZ insights
  python3 harvest_reddit.py --validate PersonalFinanceNZ tauranga
        """
    )
    
    # Main actions (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--subreddits', nargs='+', 
                             help='Subreddits to harvest (support group:name for preset groups)')
    action_group.add_argument('--list-groups', action='store_true',
                             help='List all available preset groups')
    action_group.add_argument('--validate', nargs='+',
                             help='Validate subreddits without harvesting')
    action_group.add_argument('--nz-strategy', action='store_true',
                             help='Show NZ market penetration strategy and recommendations')
    
    # Options
    parser.add_argument('--posts-per-sub', type=int, default=200,
                       help='Maximum posts per subreddit (default: 200)')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--output-name', type=str,
                       help='Custom name for output file')
    parser.add_argument('--no-validation', action='store_true',
                       help='Skip subreddit validation')
    
    # Legacy support
    parser.add_argument('legacy_subreddit', nargs='?',
                       help='Legacy: single subreddit name (for backward compatibility)')
    
    args = parser.parse_args()
    
    # Handle legacy mode
    if args.legacy_subreddit and not any([args.subreddits, args.list_groups, args.validate, args.nz_strategy]):
        args.subreddits = [args.legacy_subreddit]
        print("🔄 Legacy mode detected, using enhanced features...")
    
    # List groups action
    if args.list_groups:
        list_preset_groups(args.config)
        return 0
    
    # Validate action
    if args.validate:
        validate_subreddits_only(args.validate, args.config)
        return 0
    
    # NZ strategy action
    if args.nz_strategy:
        show_nz_strategy(args.config)
        return 0
    
    # Default to config defaults if no subreddits specified
    if not args.subreddits:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
            default_subreddits = config.get('subreddits', {}).get('default_subreddits', ['PersonalFinanceNZ'])
            args.subreddits = default_subreddits
            print(f"📋 Using default subreddits from config: {', '.join(args.subreddits)}")
        except FileNotFoundError:
            args.subreddits = ['PersonalFinanceNZ']
            print(f"📋 Using fallback default: {', '.join(args.subreddits)}")
    
    try:
        # Initialize harvester
        harvester = EnhancedRedditHarvester(args.config)
        
        # Expand subreddit inputs (handle preset groups)
        expanded_subreddits = harvester.expand_subreddit_inputs(args.subreddits)
        
        if not expanded_subreddits:
            print("❌ No valid subreddits to harvest")
            return 1
        
        print(f"📋 Final subreddit list: {', '.join(expanded_subreddits)}")
        
        # Harvest data
        all_data = harvester.harvest_multiple_subreddits(expanded_subreddits, args.posts_per_sub)
        harvester.all_data = all_data
        
        if not all_data:
            print("❌ No data harvested")
            return 1
        
        # Save data
        filename = harvester.save_data(expanded_subreddits, args.output_name)
        
        # Print comprehensive stats
        stats = harvester.get_stats()
        print(f"\n📈 ENHANCED HARVEST COMPLETE!")
        print(f"   🎯 Subreddits: {stats['subreddits_harvested']}")
        print(f"   📑 Total Posts: {stats['total_posts']:,}")
        print(f"   💬 Total Comments: {stats['total_comments']:,}")
        print(f"   📊 Total Text Pieces: {stats['total_text_pieces']:,}")
        print(f"   📅 Date Span: {stats['date_range']['span_days']} days")
        print(f"   💾 Saved to: {filename}")
        
        # Per-subreddit breakdown
        print(f"\n📊 Per-Subreddit Breakdown:")
        for subreddit, breakdown in stats['subreddit_breakdown'].items():
            posts = breakdown['posts']
            comments = breakdown['comments']
            total = posts + comments
            print(f"   r/{subreddit}: {posts:,} posts, {comments:,} comments ({total:,} total)")
        
        print(f"\n💡 Data ready for analysis! Run: python3 run_analysis.py analyze")
        
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
