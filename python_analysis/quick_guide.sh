#!/bin/bash
# Quick command guide for Enhanced Reddit Harvester

echo "🚀 ENHANCED REDDIT HARVESTER - QUICK GUIDE"
echo "=" * 50

echo ""
echo "💡 KEY IMPROVEMENTS:"
echo "• Default mode is now DELTA (90-95% faster)"
echo "• Smart harvesting - only gets new content"
echo "• Database storage - no duplicates, fast queries"
echo "• Better progress indicators and error handling"

echo ""
echo "🎯 RECOMMENDED COMMANDS:"

echo ""
echo "1️⃣  BASIC USAGE (FAST & SMART):"
echo "   python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ"
echo "   → Uses smart delta harvesting (10-30 seconds vs 3-5 minutes)"

echo ""
echo "2️⃣  MULTIPLE SUBREDDITS:"
echo "   python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ entrepreneur startups"
echo "   → Harvests all efficiently with delta mode"

echo ""
echo "3️⃣  CHECK STATUS:"
echo "   python3 harvest_reddit_enhanced.py --stats"
echo "   → See what's in your database"

echo ""
echo "4️⃣  FORCE FULL HARVEST (if needed):"
echo "   python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full"
echo "   → Comprehensive but slow (3-5 minutes)"

echo ""
echo "5️⃣  AUTOMATION:"
echo "   python3 delta_scheduler.py --status"
echo "   python3 delta_scheduler.py --run"
echo "   → Set up regular automated harvesting"

echo ""
echo "6️⃣  ANALYSIS:"
echo "   python3 run_analysis.py analyze"
echo "   → Run your existing analysis on harvested data"

echo ""
echo "🎉 MAJOR UX IMPROVEMENTS:"
echo "• 🚀 Default delta mode = 90-95% faster"
echo "• 🧠 Smart mode selection based on history"
echo "• 📊 Better progress indicators"
echo "• 💾 Persistent database storage"
echo "• 🔄 Resumable harvesting"
echo "• 😴 'No new content' detection"
echo "• 💡 Helpful next steps"
