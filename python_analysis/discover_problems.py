#!/usr/bin/env python3
"""
Smart Reddit Problem Discovery
Two-step process with intelligent caching: 1) Harvest data (if needed), 2) AI finds the problems
"""

import subprocess
import sys
import os
import time
import glob

def check_existing_harvest(subreddit_name: str) -> str:
    """Check if we have recent harvest data for this subreddit"""
    if not os.path.exists('output'):
        return None
    
    # Look for existing files for this subreddit
    pattern = f"output/reddit_{subreddit_name}_*.json"
    matching_files = glob.glob(pattern)
    
    if not matching_files:
        return None
    
    # Get the most recent file
    latest_file = max(matching_files, key=os.path.getmtime)
    
    # Check if it's recent (less than 24 hours old)
    file_age_hours = (time.time() - os.path.getmtime(latest_file)) / 3600
    
    if file_age_hours < 24:
        return latest_file
    
    return None

def check_existing_analysis(subreddit_name: str) -> str:
    """Check if we have recent analysis results for this specific subreddit"""
    if not os.path.exists('output'):
        return None
    
    # Look for recent analysis reports
    pattern = "output/opportunities_report_*.md"
    matching_files = glob.glob(pattern)
    
    if not matching_files:
        return None
    
    # Check each file to see if it's for this subreddit
    for report_file in matching_files:
        try:
            with open(report_file, 'r') as f:
                content = f.read(500)  # Read first part of file
                # Simple check if this analysis was for our subreddit
                if f"r/{subreddit_name}" in content or subreddit_name in content:
                    # Check if it's recent (less than 6 hours old)
                    file_age_hours = (time.time() - os.path.getmtime(report_file)) / 3600
                    if file_age_hours < 6:
                        return report_file
        except:
            continue
    
    return None

def main():
    """Run the complete two-step process with smart caching"""
    
    # Parse arguments
    force_refresh = '--force' in sys.argv or '-f' in sys.argv
    if force_refresh:
        sys.argv = [arg for arg in sys.argv if arg not in ['--force', '-f']]
    
    # Get subreddit name from command line or use default
    if len(sys.argv) > 1:
        subreddit_name = sys.argv[1]
    else:
        subreddit_name = "PersonalFinanceNZ"  # Default
    
    print("🚀 SMART REDDIT PROBLEM DISCOVERY")
    print("=" * 50)
    print(f"Target: r/{subreddit_name}")
    print("Smart caching: Uses existing data if recent (add --force to refresh)")
    print("=" * 50)
    
    # Check for existing analysis first
    if not force_refresh:
        existing_analysis = check_existing_analysis(subreddit_name)
        if existing_analysis:
            file_age_hours = (time.time() - os.path.getmtime(existing_analysis)) / 3600
            print(f"\n📊 Found recent analysis: {os.path.basename(existing_analysis)}")
            print(f"⏰ Analysis age: {file_age_hours:.1f} hours")
            print(f"✅ Using existing analysis (add --force to refresh)")
            print(f"📁 View report: {existing_analysis}")
            return 0
    
    # Step 1: Harvest data (smart)
    print(f"\n🏗️  STEP 1: CHECKING FOR r/{subreddit_name} DATA...")
    
    harvest_needed = True
    if not force_refresh:
        existing_harvest = check_existing_harvest(subreddit_name)
        if existing_harvest:
            file_age_hours = (time.time() - os.path.getmtime(existing_harvest)) / 3600
            print(f"💾 Found recent harvest: {os.path.basename(existing_harvest)}")
            print(f"⏰ Data age: {file_age_hours:.1f} hours")
            print(f"✅ Using existing harvest data")
            
            # Copy to latest_harvest.json for compatibility
            import shutil
            shutil.copy2(existing_harvest, 'output/latest_harvest.json')
            harvest_needed = False
    
    if harvest_needed:
        print("🔄 Harvesting new data...")
        print("Expected time: 10-30 minutes depending on Reddit API limits")
        
        try:
            if subreddit_name == "PersonalFinanceNZ":
                result = subprocess.run([sys.executable, 'harvest_reddit.py'], 
                                      capture_output=False, text=True)
            else:
                result = subprocess.run([sys.executable, 'harvest_reddit.py', subreddit_name], 
                                      capture_output=False, text=True)
            
            if result.returncode != 0:
                print("❌ Harvest failed!")
                return 1
        except Exception as e:
            print(f"❌ Harvest error: {e}")
            return 1
    
    # Step 2: AI Analysis  
    print("\n🤖 STEP 2: AI PROBLEM ANALYSIS...")
    print("This will use GPT-4 to analyze the harvested data for business problems")
    print("Expected time: 5-15 minutes depending on data size")
    
    try:
        result = subprocess.run([sys.executable, 'analyze_problems.py'], 
                              capture_output=False, text=True)
        if result.returncode != 0:
            print("❌ Analysis failed!")
            return 1
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return 1
    
    print("\n🎉 COMPLETE! Check the output/ directory for results.")
    print("📊 Look for: opportunities_report_[timestamp].md")
    
    if subreddit_name == "PersonalFinanceNZ":
        print("💡 This report contains NZ financial problems that could be business opportunities!")
    
    return 0

if __name__ == "__main__":
    # Check if we have required files
    required_files = ['harvest_reddit.py', 'analyze_problems.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Missing required file: {file}")
            sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
🚀 Smart Reddit Problem Discovery

Usage:
  python3 discover_problems.py                    # Analyze PersonalFinanceNZ (default)
  python3 discover_problems.py [subreddit_name]   # Analyze any subreddit
  python3 discover_problems.py --force            # Force refresh (ignore cache)

Examples:
  python3 discover_problems.py                    # PersonalFinanceNZ (uses cache if recent)
  python3 discover_problems.py entrepreneur       # r/entrepreneur
  python3 discover_problems.py --force            # Force fresh harvest and analysis

Smart Features:
- Uses cached harvest data if less than 24 hours old
- Uses cached analysis if less than 6 hours old
- Add --force to refresh data and analysis

What this does:
1. Harvests Reddit posts/comments (or uses cached data)
2. Uses AI clustering to group similar problems
3. Analyzes each cluster with GPT-4 for business opportunities
4. Ranks opportunities by pain level, frequency, market size
5. Generates a comprehensive business report

Results saved to: output/opportunities_report_[timestamp].md
        """)
        sys.exit(0)
    
    sys.exit(main())
