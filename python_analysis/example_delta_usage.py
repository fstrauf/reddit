#!/usr/bin/env python3
"""
Example usage of the enhanced Reddit harvester with delta fetching
This demonstrates the different harvesting modes and their use cases
"""

import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from harvest_reddit_enhanced import EnhancedRedditHarvester

def example_delta_workflow():
    """Demonstrate a typical delta harvesting workflow"""
    
    print("🚀 DELTA HARVESTING WORKFLOW EXAMPLE")
    print("=" * 50)
    
    # Initialize harvester with database enabled (default)
    harvester = EnhancedRedditHarvester()
    
    # Example 1: First time setup - harvest some subreddits fully
    print("\n📊 Step 1: Initial full harvest of key subreddits")
    print("This builds the baseline database...")
    
    initial_subreddits = ["PersonalFinanceNZ", "entrepreneur"]
    
    # Force full mode for initial setup
    data = harvester.harvest_multiple_subreddits(
        initial_subreddits, 
        max_posts_per_sub=100,  # Smaller number for demo
        force_mode='full'
    )
    
    print(f"✅ Initial harvest complete: {len(data)} posts collected")
    
    # Example 2: Delta harvest - only get new content
    print("\n🔄 Step 2: Delta harvest (run this regularly)")
    print("This fetches only new content since last harvest...")
    
    # Delta harvest will automatically skip content we already have
    delta_data = harvester.harvest_multiple_subreddits(
        initial_subreddits,
        force_mode='delta'
    )
    
    # Example 3: Mixed mode - intelligent selection
    print("\n🧠 Step 3: Intelligent mixed mode")
    print("Let the system decide delta vs full based on configuration...")
    
    mixed_subreddits = ["PersonalFinanceNZ", "newzealand", "startups"]
    
    # Auto mode uses configuration to decide delta vs full
    mixed_data = harvester.harvest_multiple_subreddits(
        mixed_subreddits,
        force_mode=None  # Auto-detect based on config
    )
    
    # Example 4: Show database statistics
    print("\n📊 Step 4: Database statistics")
    stats = harvester.get_stats()
    
    print(f"📁 Total subreddits in database: {stats['total_subreddits']}")
    print(f"📑 Total posts: {stats['total_posts']:,}")
    print(f"💬 Total comments: {stats['total_comments']:,}")
    
    print(f"\n📋 Per-subreddit breakdown:")
    for sub_data in stats['subreddit_breakdown']:
        name = sub_data['name']
        posts = sub_data['post_count']
        comments = sub_data['comment_count']
        last_harvest = sub_data.get('last_harvest_time', 'Never')
        mode = sub_data.get('harvest_mode', 'Unknown')
        
        if posts > 0:  # Only show subreddits with data
            print(f"  r/{name}: {posts} posts, {comments} comments")
            print(f"    Last harvest: {last_harvest} (mode: {mode})")

def example_configuration_scenarios():
    """Show different configuration scenarios"""
    
    print("\n🛠️  CONFIGURATION SCENARIOS")
    print("=" * 40)
    
    harvester = EnhancedRedditHarvester()
    
    # Scenario 1: High-frequency monitoring subreddits
    print("\n📈 Scenario 1: High-frequency business intelligence")
    print("Monitor fast-moving subreddits for immediate opportunities...")
    
    high_freq_subs = ["PersonalFinanceNZ", "entrepreneur", "startups"]
    
    for sub in high_freq_subs:
        print(f"  Processing r/{sub}...")
        
        # Check if we should use delta (based on config)
        use_delta = harvester.should_use_delta(sub)
        mode = "delta" if use_delta else "full"
        
        print(f"    Recommended mode: {mode}")
        
        if use_delta:
            # Delta harvest with smaller batch size for frequent updates
            stats = harvester.harvest_subreddit_delta(sub, max_posts=50)
            print(f"    Delta result: +{stats['new_posts']} posts, +{stats['new_comments']} comments")
        else:
            print(f"    Would perform full harvest...")
    
    # Scenario 2: Show different subreddit strategies
    print(f"\n🎯 Scenario 2: Subreddit-specific strategies")
    
    strategy_examples = {
        "PersonalFinanceNZ": "High-frequency delta for timely financial problems",
        "entrepreneur": "Medium-frequency delta for business opportunities", 
        "AskReddit": "Weekly full harvest for broad problem discovery",
        "mildlyinfuriating": "Monthly full harvest for frustration analysis"
    }
    
    for sub, strategy in strategy_examples.items():
        use_delta = harvester.should_use_delta(sub)
        current_mode = "delta" if use_delta else "full"
        print(f"  r/{sub}: {strategy}")
        print(f"    Current config: {current_mode} mode")

def example_database_queries():
    """Demonstrate database query capabilities"""
    
    print("\n🔍 DATABASE QUERY EXAMPLES")
    print("=" * 40)
    
    harvester = EnhancedRedditHarvester()
    
    # Direct database access for advanced queries
    if harvester.db:
        with harvester.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Example 1: Recent activity summary
            print("\n📊 Recent activity (last 24 hours):")
            cursor.execute("""
                SELECT s.name, COUNT(p.id) as recent_posts
                FROM subreddits s
                LEFT JOIN posts p ON s.id = p.subreddit_id 
                    AND p.created_utc > ?
                GROUP BY s.id
                HAVING recent_posts > 0
                ORDER BY recent_posts DESC
            """, (int((datetime.now().timestamp() - 86400)),))  # 24 hours ago
            
            recent_activity = cursor.fetchall()
            for row in recent_activity:
                print(f"  r/{row['name']}: {row['recent_posts']} posts")
            
            # Example 2: Checkpoint status
            print(f"\n🎯 Checkpoint status:")
            cursor.execute("""
                SELECT s.name, hc.last_harvest_time, hc.harvest_mode,
                       hc.total_posts_harvested, hc.total_comments_harvested
                FROM harvest_checkpoints hc
                JOIN subreddits s ON hc.subreddit_id = s.id
                ORDER BY hc.last_harvest_time DESC
            """)
            
            checkpoints = cursor.fetchall()
            for row in checkpoints:
                name = row['name']
                last_time = row['last_harvest_time']
                mode = row['harvest_mode']
                posts = row['total_posts_harvested']
                comments = row['total_comments_harvested']
                
                print(f"  r/{name}: {posts} posts, {comments} comments")
                print(f"    Last: {last_time} ({mode} mode)")

def main():
    """Run the example workflows"""
    
    print("🎯 ENHANCED REDDIT HARVESTER - DELTA FETCHING EXAMPLES")
    print("=" * 60)
    print("This example demonstrates the delta harvesting capabilities")
    print("that allow efficient incremental data collection.")
    print()
    
    try:
        # Run the examples
        example_delta_workflow()
        example_configuration_scenarios()
        example_database_queries()
        
        print(f"\n✅ EXAMPLES COMPLETE!")
        print(f"\n💡 Key Benefits of Delta Harvesting:")
        print(f"   🚀 Much faster harvesting (only new content)")
        print(f"   💾 Persistent storage in SQLite database")
        print(f"   🔄 Resume harvesting from where you left off")
        print(f"   📊 Built-in analytics and statistics")
        print(f"   ⚡ Efficient for real-time monitoring")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Configure delta_enabled_subreddits in config.json")
        print(f"   2. Run initial full harvest: --mode full")
        print(f"   3. Set up regular delta harvests: --mode delta")
        print(f"   4. Monitor with: --stats")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
