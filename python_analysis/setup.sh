#!/bin/bash
# Setup script for Enhanced Reddit Harvester
# This script activates the virtual environment and provides helpful commands

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Enhanced Reddit Harvester Setup${NC}"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "harvest_reddit_enhanced.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the python_analysis directory${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import praw" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not found. Installing...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
fi

# Test imports
echo -e "${BLUE}🧪 Testing imports...${NC}"
if python -c "from harvest_reddit_enhanced import EnhancedRedditHarvester" 2>/dev/null; then
    echo -e "${GREEN}✅ Enhanced harvester imports successfully${NC}"
else
    echo -e "${RED}❌ Import test failed${NC}"
    exit 1
fi

# Check database status
echo -e "${BLUE}📊 Database status:${NC}"
python harvest_reddit_enhanced.py --stats

echo ""
echo -e "${GREEN}🎯 Setup complete! Here are some example commands:${NC}"
echo ""
echo -e "${YELLOW}Basic Commands:${NC}"
echo "  # Check database status"
echo "  python harvest_reddit_enhanced.py --stats"
echo ""
echo "  # Small test harvest (10 posts)"
echo "  python harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full --posts-per-sub 10"
echo ""
echo "  # Delta harvest (only new content)"
echo "  python harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode delta"
echo ""
echo -e "${YELLOW}Automation Commands:${NC}"
echo "  # Check scheduled status"
echo "  python delta_scheduler.py --status"
echo ""
echo "  # Run scheduled harvests"
echo "  python delta_scheduler.py --run"
echo ""
echo -e "${YELLOW}Analysis Commands:${NC}"
echo "  # Run your existing analysis"
echo "  python run_analysis.py analyze"
echo ""
echo "  # Full pipeline (harvest + analyze)"
echo "  python run_analysis.py full --subreddits PersonalFinanceNZ"
echo ""
echo -e "${BLUE}💡 Virtual Environment:${NC}"
echo "  To manually activate: source venv/bin/activate"
echo "  To deactivate: deactivate"
echo ""
echo -e "${GREEN}✅ You're ready to go! The virtual environment is activated.${NC}"

# Keep the environment activated for the user
exec bash
