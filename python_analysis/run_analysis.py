#!/usr/bin/env python3
"""
Enhanced Reddit Problem Analysis Orchestrator
Runs the complete enhanced analysis pipeline with cost optimization
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'openai', 'textblob', 'pandas', 'numpy', 'scikit-learn',
        'sentence-transformers', 'matplotlib', 'seaborn', 'plotly', 'wordcloud'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("💡 Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies found")
    return True

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment...")
    
    # Check for OpenAI API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("💡 Set it in .env.local file or environment variables")
        return False
    
    # Check for harvest data
    harvest_file = 'output/latest_harvest.json'
    if not os.path.exists(harvest_file):
        print(f"⚠️  No harvest file found at {harvest_file}")
        print("💡 Run harvest_reddit.py first to collect data")
        return False
    
    print("✅ Environment configured correctly")
    return True

def show_config_info():
    """Show current configuration"""
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("\n📋 Current Configuration:")
        print(f"   🎯 Max API Calls: {config['analysis'].get('max_api_calls', 50)}")
        print(f"   💰 Smart Filtering: {config['cost_optimization'].get('enable_smart_filtering', True)}")
        print(f"   📊 Visualizations: {config['visualization'].get('enable_charts', True)}")
        print(f"   🔄 Incremental Mode: {config['incremental'].get('enable_incremental', False)}")
        print(f"   🕐 Temporal Analysis: {config['temporal'].get('enable_temporal_analysis', True)}")
        
        estimated_cost = config['analysis'].get('max_api_calls', 50) * config['cost_optimization'].get('estimated_cost_per_call', 0.002)
        print(f"   💵 Max Estimated Cost: ${estimated_cost:.3f}")
    else:
        print("⚠️  No config.json found, will use defaults")

def run_harvest(subreddits=None, posts_per_sub=200, config='config.json', output_name=None):
    """Run the enhanced harvest script to collect fresh data"""
    print("🌾 Running Enhanced Reddit Harvest...")
    
    cmd = ['python3', 'harvest_reddit.py']
    
    # Add subreddits (support preset groups)
    if subreddits:
        cmd.extend(['--subreddits'] + subreddits)
    
    # Add other options
    if posts_per_sub != 200:
        cmd.extend(['--posts-per-sub', str(posts_per_sub)])
    if config != 'config.json':
        cmd.extend(['--config', config])
    if output_name:
        cmd.extend(['--output-name', output_name])
    
    try:
        # Run with real-time output for better user experience
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        
        for line in process.stdout:
            print(line.rstrip())
        
        process.wait()
        
        if process.returncode == 0:
            print("✅ Enhanced harvest completed successfully")
            return True
        else:
            print(f"❌ Harvest failed with code {process.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running harvest: {e}")
        return False

def run_enhanced_analysis(args):
    """Run the enhanced analysis"""
    print("🚀 Running Enhanced Analysis...")
    
    cmd = ['python3', 'analyze_problems.py']
    
    if args.basic:
        cmd.append('--basic')
    if args.max_problems != 1000:
        cmd.extend(['--max-problems', str(args.max_problems)])
    if args.clusters != 15:
        cmd.extend(['--clusters', str(args.clusters)])
    if args.config != 'config.json':
        cmd.extend(['--config', args.config])
    if args.harvest_file:
        cmd.extend(['--harvest-file', args.harvest_file])
    
    try:
        # Run with real-time output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, bufsize=1)
        
        for line in process.stdout:
            print(line.rstrip())
        
        process.wait()
        
        if process.returncode == 0:
            print("\n✅ Enhanced analysis completed successfully!")
            print("📊 Check output/ directory for results:")
            print("   📈 enhanced_report_*.md - Full analysis report")
            print("   📋 enhanced_opportunities_*.json - Raw data")
            print("   📊 charts/ - Visualizations")
            return True
        else:
            print(f"❌ Analysis failed with code {process.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Enhanced Reddit Problem Analysis Orchestrator')
    
    # Main commands
    parser.add_argument('command', nargs='?', choices=['harvest', 'analyze', 'full', 'status'], 
                       default='analyze', help='Command to run (default: analyze)')
    
    # Analysis options
    parser.add_argument('--basic', action='store_true', 
                       help='Run basic analysis only (no enhanced features)')
    parser.add_argument('--max-problems', type=int, default=1000,
                       help='Maximum problems to analyze (default: 1000)')
    parser.add_argument('--clusters', type=int, default=15,
                       help='Number of clusters (default: 15)')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Configuration file (default: config.json)')
    parser.add_argument('--harvest-file', type=str,
                       help='Custom harvest file to analyze')
    
    # Harvest options
    parser.add_argument('--subreddits', nargs='+',
                       help='Subreddits to harvest (supports group:name for preset groups)')
    parser.add_argument('--posts-per-sub', type=int, default=200,
                       help='Posts per subreddit (default: 200)')
    parser.add_argument('--output-name', type=str,
                       help='Custom name for harvest output file')
    
    # Subreddit management
    parser.add_argument('--list-groups', action='store_true',
                       help='List available preset subreddit groups')
    parser.add_argument('--validate-subs', nargs='+',
                       help='Validate subreddits without harvesting')
    parser.add_argument('--nz-strategy', action='store_true',
                       help='Show NZ market penetration strategy and recommendations')
    
    # Force options
    parser.add_argument('--force', action='store_true',
                       help='Skip dependency/environment checks')
    
    args = parser.parse_args()
    
    print("🎯 Enhanced Reddit Problem Analysis")
    print("=" * 50)
    
    # Handle subreddit management commands
    if args.list_groups:
        print("📦 Listing preset subreddit groups...")
        try:
            result = subprocess.run(['python3', 'harvest_reddit.py', '--list-groups'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except Exception as e:
            print(f"❌ Error listing groups: {e}")
        return
    
    if args.validate_subs:
        print("🔍 Validating subreddits...")
        try:
            cmd = ['python3', 'harvest_reddit.py', '--validate'] + args.validate_subs
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except Exception as e:
            print(f"❌ Error validating subreddits: {e}")
        return
    
    if args.nz_strategy:
        print("🥝 Showing NZ market strategy...")
        try:
            result = subprocess.run(['python3', 'harvest_reddit.py', '--nz-strategy'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except Exception as e:
            print(f"❌ Error showing NZ strategy: {e}")
        return
    
    # Status command
    if args.command == 'status':
        print("📊 System Status:")
        deps_ok = check_dependencies()
        env_ok = check_environment()
        show_config_info()
        
        if deps_ok and env_ok:
            print("\n✅ System ready for analysis")
        else:
            print("\n❌ System not ready - fix issues above")
        return
    
    # Check system unless forced
    if not args.force:
        if not check_dependencies():
            print("❌ Fix dependencies before continuing")
            return
        if not check_environment():
            print("❌ Fix environment before continuing")
            return
    
    show_config_info()
    
    # Execute commands
    if args.command == 'harvest':
        success = run_harvest(args.subreddits, args.posts_per_sub, args.config, args.output_name)
        if not success:
            sys.exit(1)
    
    elif args.command == 'analyze':
        success = run_enhanced_analysis(args)
        if not success:
            sys.exit(1)
    
    elif args.command == 'full':
        print("🔄 Running full enhanced pipeline: harvest + analyze")
        
        # First harvest
        harvest_success = run_harvest(args.subreddits, args.posts_per_sub, args.config, args.output_name)
        if not harvest_success:
            print("❌ Harvest failed, stopping pipeline")
            sys.exit(1)
        
        print("\n" + "="*50 + "\n")
        
        # Then analyze
        analyze_success = run_enhanced_analysis(args)
        if not analyze_success:
            print("❌ Analysis failed")
            sys.exit(1)
        
        print("\n🎉 Full pipeline completed successfully!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
