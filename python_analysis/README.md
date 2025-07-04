# 🚀 Smart Reddit Problem Discovery

AI-powered tool to discover business opportunities from Reddit discussions using embeddings and clustering.

## ✨ Smart Caching System

This tool now includes **intelligent caching** to save time and API costs:
- **Harvest cache**: Uses existing data if less than 24 hours old
- **Analysis cache**: Uses existing analysis if less than 6 hours old  
- **Force refresh**: Add `--force` to ignore cache and get fresh data

## 📁 Files

- `harvest_reddit.py` - Harvests posts and comments from any subreddit (with smart caching)
- `analyze_problems.py` - **Smart analyzer** using embeddings + GPT-4
- `discover_problems.py` - Runs both steps automatically (with smart caching)
- `requirements.txt` - Python dependencies

## 🚀 Quick Start

```bash
# Default: Analyze PersonalFinanceNZ (uses cache if recent)
python3 discover_problems.py

# Analyze any subreddit (uses cache if available)
python3 discover_problems.py entrepreneur

# Force fresh data and analysis
python3 discover_problems.py --force
```

## 🧠 How It Works

1. **Smart Check** - Looks for recent data and analysis first
2. **Harvest** - Collects posts and comments from Reddit (if needed)
3. **Extract** - Finds texts containing problem indicators
4. **Embed** - Creates semantic embeddings for all problem texts
5. **Cluster** - Groups similar problems using K-means clustering
6. **Analyze** - Uses GPT-4 to analyze each cluster for business opportunities
7. **Rank** - Scores opportunities by pain level, frequency, market size, etc.

## 🎯 Smart Features

- **Intelligent caching** - Avoids unnecessary API calls and saves time
- **Embedding similarity** - Groups truly similar problems together
- **Cluster analysis** - Analyzes representative samples from each cluster
- **Multi-factor scoring** - Pain level + frequency + market size + implementation difficulty
- **Cost efficient** - Uses GPT-4o-mini for analysis (cheaper, faster)
- **Scalable** - Can handle thousands of problems efficiently

## ⚡ Caching Behavior

```bash
# First run: Fresh harvest + analysis
python3 discover_problems.py
# → Takes 15-30 minutes

# Second run (within 6 hours): Uses cached analysis
python3 discover_problems.py  
# → Takes 0 seconds

# Force refresh: Ignores all cache
python3 discover_problems.py --force
# → Takes 15-30 minutes (fresh data)
```

## 📊 Output

Generates a comprehensive report with:
- Top business opportunities ranked by potential
- Pain levels and market size estimates
- Potential solutions and target audiences
- Sample problems from real Reddit discussions
- Implementation difficulty assessments

## 🇳🇿 PersonalFinanceNZ Focus

Default target: r/PersonalFinanceNZ (124K subscribers)
- High-quality financial discussions
- Real NZ market problems
- Validated pain points with business potential

## ⚙️ Advanced Usage

```bash
# Analyze more problems with more clusters
python3 analyze_problems.py 500 20

# Force fresh harvest only
python3 harvest_reddit.py --force

# Custom parameters: max_problems n_clusters
python3 analyze_problems.py 1000 25
```

## 📋 Requirements

- Reddit API credentials in `../.env.local`
- OpenAI API key for GPT-4 analysis
- Python 3.8+ with required packages
