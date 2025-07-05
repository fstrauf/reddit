#!/usr/bin/env python3
"""
Automated Delta Harvesting Scheduler
Run this script regularly (via cron/systemd) for automated delta harvesting
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from harvest_reddit_enhanced import EnhancedRedditHarvester

class DeltaScheduler:
    """Automated scheduler for delta harvesting"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.harvester = EnhancedRedditHarvester(config_file)
        self.config = self.harvester.config
        
    def get_subreddits_due_for_harvest(self) -> Dict[str, List[str]]:
        """Get subreddits that are due for harvesting based on schedule"""
        
        if not self.harvester.use_database:
            return {"high_frequency": [], "medium_frequency": [], "low_frequency": []}
        
        delta_config = self.config.get('delta', {})
        schedule_config = delta_config.get('delta_schedule', {})
        
        due_subreddits = {
            "high_frequency": [],
            "medium_frequency": [], 
            "low_frequency": []
        }
        
        current_time = datetime.now()
        
        # Check each frequency tier
        for frequency, freq_config in schedule_config.items():
            interval_hours = freq_config.get('interval_hours', 24)
            subreddits = freq_config.get('subreddits', [])
            
            for subreddit_name in subreddits:
                # Get subreddit checkpoint
                subreddit_id = self.harvester.db.get_or_create_subreddit(subreddit_name)
                checkpoint = self.harvester.db.get_checkpoint(subreddit_id)
                
                is_due = False
                
                if not checkpoint or not checkpoint.last_harvest_time:
                    # Never harvested before
                    is_due = True
                else:
                    # Check if enough time has passed
                    time_since_harvest = current_time - checkpoint.last_harvest_time
                    if time_since_harvest.total_seconds() >= (interval_hours * 3600):
                        is_due = True
                
                if is_due:
                    due_subreddits[frequency].append(subreddit_name)
        
        return due_subreddits
    
    def run_scheduled_harvest(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run scheduled delta harvests"""
        
        print(f"🕒 SCHEDULED DELTA HARVEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual harvesting will be performed")
        
        due_subreddits = self.get_subreddits_due_for_harvest()
        
        total_due = sum(len(subs) for subs in due_subreddits.values())
        
        if total_due == 0:
            print("✅ No subreddits due for harvesting")
            return {"status": "no_work", "subreddits_processed": 0}
        
        print(f"📊 Found {total_due} subreddits due for harvesting:")
        
        for frequency, subreddits in due_subreddits.items():
            if subreddits:
                interval = self.config.get('delta', {}).get('delta_schedule', {}).get(frequency, {}).get('interval_hours', 'unknown')
                print(f"  {frequency}: {len(subreddits)} subreddits (every {interval}h)")
                for sub in subreddits:
                    print(f"    - r/{sub}")
        
        if dry_run:
            return {"status": "dry_run", "subreddits_due": total_due}
        
        # Perform harvests
        harvest_results = []
        
        for frequency, subreddits in due_subreddits.items():
            if not subreddits:
                continue
                
            freq_config = self.config.get('delta', {}).get('delta_schedule', {}).get(frequency, {})
            max_posts = freq_config.get('max_posts', 100)
            
            print(f"\n🔄 Processing {frequency} subreddits (max {max_posts} posts each):")
            
            for subreddit_name in subreddits:
                try:
                    print(f"  📊 Harvesting r/{subreddit_name}...")
                    
                    stats = self.harvester.harvest_subreddit_delta(
                        subreddit_name, 
                        max_posts=max_posts
                    )
                    
                    harvest_results.append({
                        'subreddit': subreddit_name,
                        'frequency': frequency,
                        'success': True,
                        'new_posts': stats['new_posts'],
                        'new_comments': stats['new_comments']
                    })
                    
                    print(f"    ✅ +{stats['new_posts']} posts, +{stats['new_comments']} comments")
                    
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    
                    harvest_results.append({
                        'subreddit': subreddit_name,
                        'frequency': frequency,
                        'success': False,
                        'error': str(e)
                    })
        
        # Summary
        successful_harvests = [r for r in harvest_results if r['success']]
        failed_harvests = [r for r in harvest_results if not r['success']]
        
        total_new_posts = sum(r['new_posts'] for r in successful_harvests)
        total_new_comments = sum(r['new_comments'] for r in successful_harvests)
        
        print(f"\n📊 HARVEST SUMMARY:")
        print(f"✅ Successful: {len(successful_harvests)} subreddits")
        print(f"❌ Failed: {len(failed_harvests)} subreddits")
        print(f"📑 New posts: {total_new_posts}")
        print(f"💬 New comments: {total_new_comments}")
        
        if failed_harvests:
            print(f"\n❌ Failed harvests:")
            for failed in failed_harvests:
                print(f"  r/{failed['subreddit']}: {failed['error']}")
        
        # Database stats
        db_stats = self.harvester.get_stats()
        print(f"\n💾 Database totals: {db_stats['total_posts']:,} posts, {db_stats['total_comments']:,} comments")
        
        return {
            "status": "completed",
            "subreddits_processed": len(harvest_results),
            "successful_harvests": len(successful_harvests),
            "failed_harvests": len(failed_harvests),
            "new_posts": total_new_posts,
            "new_comments": total_new_comments,
            "harvest_results": harvest_results
        }
    
    def get_harvest_status(self) -> Dict[str, Any]:
        """Get current harvest status for all configured subreddits"""
        
        delta_config = self.config.get('delta', {})
        schedule_config = delta_config.get('delta_schedule', {})
        
        status = {}
        
        for frequency, freq_config in schedule_config.items():
            interval_hours = freq_config.get('interval_hours', 24)
            subreddits = freq_config.get('subreddits', [])
            
            for subreddit_name in subreddits:
                subreddit_id = self.harvester.db.get_or_create_subreddit(subreddit_name)
                checkpoint = self.harvester.db.get_checkpoint(subreddit_id)
                
                if checkpoint and checkpoint.last_harvest_time:
                    time_since = datetime.now() - checkpoint.last_harvest_time
                    hours_since = time_since.total_seconds() / 3600
                    next_due = max(0, interval_hours - hours_since)
                    
                    status[subreddit_name] = {
                        'frequency': frequency,
                        'interval_hours': interval_hours,
                        'last_harvest': checkpoint.last_harvest_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'hours_since_last': round(hours_since, 1),
                        'next_due_hours': round(next_due, 1),
                        'is_due': next_due <= 0,
                        'total_posts': checkpoint.posts_harvested,
                        'total_comments': checkpoint.comments_harvested
                    }
                else:
                    status[subreddit_name] = {
                        'frequency': frequency,
                        'interval_hours': interval_hours,
                        'last_harvest': 'Never',
                        'hours_since_last': float('inf'),
                        'next_due_hours': 0,
                        'is_due': True,
                        'total_posts': 0,
                        'total_comments': 0
                    }
        
        return status


def main():
    """Main CLI interface for delta scheduling"""
    
    parser = argparse.ArgumentParser(
        description='Automated Delta Harvesting Scheduler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check what's due for harvest
  python3 delta_scheduler.py --status
  
  # Dry run (see what would be harvested)
  python3 delta_scheduler.py --run --dry-run
  
  # Run scheduled harvests
  python3 delta_scheduler.py --run
  
  # Force harvest specific subreddits
  python3 delta_scheduler.py --force PersonalFinanceNZ entrepreneur
  
Cron Examples:
  # Every 2 hours for high-frequency subreddits
  0 */2 * * * cd /path/to/reddit && python3 delta_scheduler.py --run
  
  # Daily summary
  0 8 * * * cd /path/to/reddit && python3 delta_scheduler.py --status
        """
    )
    
    # Main actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--run', action='store_true',
                             help='Run scheduled delta harvests')
    action_group.add_argument('--status', action='store_true',
                             help='Show harvest status for all subreddits')
    action_group.add_argument('--force', nargs='+',
                             help='Force harvest specific subreddits')
    
    # Options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be harvested without doing it')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        scheduler = DeltaScheduler(args.config)
        
        # Handle status request
        if args.status:
            print("📊 HARVEST STATUS")
            print("=" * 40)
            
            status = scheduler.get_harvest_status()
            
            # Group by frequency
            by_frequency = {}
            for sub, info in status.items():
                freq = info['frequency']
                if freq not in by_frequency:
                    by_frequency[freq] = []
                by_frequency[freq].append((sub, info))
            
            for frequency in ['high_frequency', 'medium_frequency', 'low_frequency']:
                if frequency in by_frequency:
                    interval = by_frequency[frequency][0][1]['interval_hours']
                    print(f"\n🎯 {frequency.replace('_', ' ').title()} (every {interval}h):")
                    
                    for sub, info in by_frequency[frequency]:
                        due_status = "🔴 DUE" if info['is_due'] else f"🟢 {info['next_due_hours']:.1f}h"
                        last_harvest = info['last_harvest']
                        posts = info['total_posts']
                        comments = info['total_comments']
                        
                        print(f"  r/{sub}: {due_status}")
                        print(f"    Last: {last_harvest} | Total: {posts} posts, {comments} comments")
            
            return 0
        
        # Handle force harvest
        if args.force:
            print(f"🔄 FORCE HARVEST")
            print(f"Subreddits: {', '.join(args.force)}")
            
            if args.dry_run:
                print("🧪 DRY RUN - Would harvest these subreddits")
                return 0
            
            for subreddit_name in args.force:
                try:
                    print(f"\n📊 Force harvesting r/{subreddit_name}...")
                    stats = scheduler.harvester.harvest_subreddit_delta(subreddit_name)
                    print(f"✅ +{stats['new_posts']} posts, +{stats['new_comments']} comments")
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            return 0
        
        # Handle scheduled run
        if args.run:
            results = scheduler.run_scheduled_harvest(dry_run=args.dry_run)
            
            if results['status'] == 'no_work':
                print("😴 No work to do - all subreddits are up to date")
                return 0
            elif results['status'] == 'dry_run':
                print(f"🧪 Dry run complete - {results['subreddits_due']} subreddits would be harvested")
                return 0
            else:
                print(f"✅ Scheduled harvest complete!")
                return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
