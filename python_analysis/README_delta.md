# Enhanced Reddit Harvester with Delta Fetching

This enhanced version of the Reddit harvester adds intelligent delta fetching capabilities, allowing you to efficiently collect only new content since your last harvest. This is perfect for real-time monitoring and large-scale data collection.

## 🚀 Key Features

### Delta Harvesting
- **Incremental Updates**: Only fetch new posts/comments since last harvest
- **Persistent Storage**: SQLite database stores all data with checkpoints
- **Smart Resumption**: Resume harvesting exactly where you left off
- **Performance**: 10-50x faster than full harvests for regular monitoring

### Intelligent Mode Selection
- **Auto-detection**: Automatically choose delta vs full harvest based on configuration
- **Subreddit-specific**: Configure different strategies per subreddit
- **Frequency-based**: High/medium/low frequency scheduling for different subreddits

### Backward Compatibility
- **Original Features**: All original harvesting features still work
- **File Output**: Still generates JSON files for existing analysis scripts
- **Configuration**: Extends existing config.json without breaking changes

## 📋 Quick Start

### 1. Initial Setup

```bash
# Install any additional dependencies
pip install sqlite3  # Usually included with Python

# Run initial harvest to populate database
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full

# Check database status
python3 harvest_reddit_enhanced.py --stats
```

### 2. Delta Harvesting

```bash
# Harvest only new content (delta mode)
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode delta

# Auto mode (uses config to decide delta vs full)
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ entrepreneur

# Multiple subreddits with different strategies
python3 harvest_reddit_enhanced.py --subreddits group:nz_primary_targets
```

### 3. Automated Scheduling

```bash
# Check what's due for harvest
python3 delta_scheduler.py --status

# Run scheduled harvests
python3 delta_scheduler.py --run

# Force harvest specific subreddits
python3 delta_scheduler.py --force PersonalFinanceNZ entrepreneur
```

## ⚙️ Configuration

### Delta Configuration in `config.json`

```json
{
  "delta": {
    "enabled_subreddits": [
      "PersonalFinanceNZ",
      "newzealand", 
      "entrepreneur",
      "startups"
    ],
    "full_harvest_subreddits": [
      "AskReddit",
      "unpopularopinion"
    ],
    "delta_max_posts": 100,
    "full_max_posts": 500,
    "delta_schedule": {
      "high_frequency": {
        "subreddits": ["PersonalFinanceNZ", "entrepreneur"],
        "interval_hours": 2,
        "max_posts": 50
      },
      "medium_frequency": {
        "subreddits": ["newzealand", "auckland"],
        "interval_hours": 6,
        "max_posts": 100
      },
      "low_frequency": {
        "subreddits": ["wellington", "programming"],
        "interval_hours": 24,
        "max_posts": 200
      }
    }
  }
}
```

### Subreddit Strategy Guidelines

**Use Delta For:**
- High-activity subreddits you monitor regularly
- Business intelligence targets (PersonalFinanceNZ, entrepreneur)
- Local communities (newzealand, auckland)
- Tech communities with frequent updates

**Use Full Harvest For:**
- Large general subreddits (AskReddit)
- One-time analysis targets
- Historical data collection
- Subreddits you check infrequently

## 🔄 Usage Modes

### 1. Database Mode (Recommended)
```bash
# Default - uses SQLite database for efficient storage
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ

# Check database statistics
python3 harvest_reddit_enhanced.py --stats
```

### 2. Original File Mode
```bash
# Disable database, use original JSON file output
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --no-database

# Still creates output/reddit_*.json files
```

### 3. Mixed Mode
```bash
# Database storage + JSON export for analysis
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full
# Creates both database entries AND JSON files
```

## 🕒 Automated Scheduling

### Cron Setup

```bash
# Edit crontab
crontab -e

# Add these lines for automated harvesting:

# Every 2 hours - high frequency subreddits
0 */2 * * * cd /path/to/reddit/python_analysis && python3 delta_scheduler.py --run

# Every 6 hours - medium frequency  
0 */6 * * * cd /path/to/reddit/python_analysis && python3 delta_scheduler.py --run

# Daily summary report
0 8 * * * cd /path/to/reddit/python_analysis && python3 delta_scheduler.py --status
```

### Systemd Timer (Alternative)

```bash
# Create service file
sudo nano /etc/systemd/system/reddit-harvest.service

# Add timer file
sudo nano /etc/systemd/system/reddit-harvest.timer

# Enable and start
sudo systemctl enable reddit-harvest.timer
sudo systemctl start reddit-harvest.timer
```

## 📊 Database Structure

### Tables Created
- **subreddits**: Subreddit metadata and statistics
- **posts**: All harvested posts with full content
- **comments**: All harvested comments with threading info
- **harvest_checkpoints**: Track harvesting progress per subreddit

### Key Benefits
- **Full-text Search**: Built-in search capabilities
- **Relationships**: Proper foreign keys between posts/comments
- **Performance**: Indexed for fast queries
- **Analytics**: Rich metadata for analysis

## 🔍 Advanced Usage

### Database Queries
```python
from harvest_reddit_enhanced import EnhancedRedditHarvester

harvester = EnhancedRedditHarvester()

# Direct database access
with harvester.db.get_connection() as conn:
    cursor = conn.cursor()
    
    # Find recent posts
    cursor.execute("""
        SELECT title, score, created_utc 
        FROM posts 
        WHERE created_utc > ? 
        ORDER BY score DESC
    """, (recent_timestamp,))
```

### Custom Analysis Pipeline
```python
# Get database stats
stats = harvester.get_stats()

# Export recent data for analysis  
recent_data = harvester.db.get_recent_posts(subreddit_id, hours=24)

# Full-text search
problems = harvester.db.search_problems("problem OR issue OR help")
```

### Reset Checkpoints
```bash
# Reset checkpoint for a subreddit (will re-harvest everything)
python3 harvest_reddit_enhanced.py --reset-checkpoint PersonalFinanceNZ
```

## 🎯 Best Practices

### 1. Start Small
```bash
# Begin with a few key subreddits
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full

# Add more as you scale
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ entrepreneur --mode delta
```

### 2. Monitor Performance
```bash
# Regular status checks
python3 harvest_reddit_enhanced.py --stats

# Check what's due for harvest
python3 delta_scheduler.py --status
```

### 3. Configure Frequencies
- **High (2h)**: Critical business intelligence subreddits
- **Medium (6h)**: Important community monitoring
- **Low (24h)**: General discovery and trends

### 4. Backup Strategy
```bash
# Backup database
cp output/reddit_data.db output/reddit_data_backup_$(date +%Y%m%d).db

# Export for analysis
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full --output-name backup
```

## 🔧 Troubleshooting

### Common Issues

1. **"No new content found"**
   - Check if subreddit is active
   - Verify checkpoint timestamps
   - Consider resetting checkpoint

2. **Database locked errors**
   - Check for concurrent processes
   - Restart harvest process
   - Verify file permissions

3. **Rate limiting**
   - Reduce max_posts in config
   - Increase delays between requests
   - Monitor Reddit API status

### Debug Commands
```bash
# Check database status
python3 harvest_reddit_enhanced.py --stats

# Validate subreddits
python3 harvest_reddit.py --validate PersonalFinanceNZ

# Reset problematic checkpoint
python3 harvest_reddit_enhanced.py --reset-checkpoint PersonalFinanceNZ

# Force full re-harvest
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full
```

## 🚀 Migration from Original

### Step 1: Backup Existing Data
```bash
# Backup your existing JSON files
mkdir -p output/backup
cp output/*.json output/backup/
```

### Step 2: Run Enhanced Version
```bash
# First run builds database from scratch
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode full
```

### Step 3: Configure Delta Settings
```bash
# Edit config.json to add delta configuration
# Start with a few key subreddits for delta harvesting
```

### Step 4: Test and Scale
```bash
# Test delta harvesting
python3 harvest_reddit_enhanced.py --subreddits PersonalFinanceNZ --mode delta

# Scale up gradually
python3 delta_scheduler.py --run
```

## 📈 Performance Benefits

### Delta vs Full Harvest Comparison

| Aspect | Full Harvest | Delta Harvest |
|--------|-------------|---------------|
| **Speed** | 5-10 minutes | 10-30 seconds |
| **API Calls** | 500-2000 | 50-200 |
| **Storage** | Duplicate data | Incremental only |
| **Memory** | High | Low |
| **Suitable For** | Initial setup, analysis | Real-time monitoring |

### Typical Performance
- **PersonalFinanceNZ Delta**: 10-50 new posts per day
- **entrepreneur Delta**: 100-300 new posts per day  
- **Processing Time**: 95% reduction vs full harvest
- **Storage Efficiency**: No duplicate data

This enhanced harvester enables real-time Reddit monitoring at scale while maintaining all the original analysis capabilities.
