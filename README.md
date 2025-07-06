# Reddit Sentiment Analyzer

A powerful tool to analyze Reddit communities and discover business opportunities by examining sentiment, common problems, and trending topics in discussions.

## Features

- **Sentiment Analysis**: Analyze the overall mood and sentiment of Reddit communities
- **Business Opportunity Detection**: Identify potential business opportunities from recurring problems and discussions
- **Common Problem Identification**: Find pain points that community members frequently discuss
- **Trending Topics**: Discover what topics are generating the most engagement
- **Comprehensive Analytics**: Get detailed breakdowns of sentiment, keywords, and frequency data

## Target Use Cases

- Market research for new business ideas
- Identifying underserved market segments
- Understanding community pain points
- Competitor analysis
- Product development insights
- Content strategy planning

## Setup

Make sure to install dependencies:

```bash
# pnpm (recommended)
pnpm install

# npm
npm install

# yarn
yarn install
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# OpenAI API Key (required for sentiment analysis)
NUXT_OPENAI_API_KEY=your_openai_api_key_here

# Reddit API Credentials (required for accessing Reddit data)
NUXT_REDDIT_CLIENT_ID=your_reddit_client_id
NUXT_REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

### Getting Reddit API Credentials

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Choose "script" as the app type
4. Fill in the required fields (name, description, redirect URI can be http://localhost)
5. Copy the client ID (under the app name) and client secret

### Getting OpenAI API Key

1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key to your `.env` file

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# pnpm
pnpm dev

# npm
npm run dev

# yarn
yarn dev
```

### macOS Users: Fixing "too many open files" Error

If you encounter an `EMFILE: too many open files, watch` error on macOS, use the special development script that increases the file descriptor limit:

```bash
# pnpm
pnpm dev:macos

# npm
npm run dev:macos

# yarn
yarn dev:macos
```

This script automatically increases the file descriptor limit to 10240 before starting the development server, which resolves the issue caused by macOS's default low limit.

**Additional Fix**: The Nuxt configuration has been updated to exclude the `python_analysis/` directory from file watching, preventing the development server from monitoring thousands of Python package files in the virtual environment. This significantly reduces the number of file watchers needed.

## Usage

### Basic Sentiment Analysis

1. Enter a subreddit name (e.g., "PersonalFinanceNZ")
2. Select the number of posts to analyze (25, 50, or 100)
3. Click "Analyze Sentiment & Find Opportunities"
4. Review the results:
   - **Business Opportunities**: Potential business ideas based on community needs
   - **Common Problems**: Frequently mentioned issues and pain points
   - **Trending Topics**: Popular discussion themes
   - **Sentiment Analysis**: Overall mood breakdown of the community

### Advanced Python Analysis

The application also includes a more powerful Python-based analysis tool with additional features:

1. Navigate to the "Python Analysis" page using the navigation bar
2. Select the harvest mode:
   - **Smart**: Auto delta mode (recommended for regular use)
   - **Delta**: Fast updates only
   - **Full**: Complete scan (slower but comprehensive)
3. Add subreddits individually or select from preset groups
4. Configure options like posts per subreddit and output name
5. Click "Start Harvest" to begin the analysis
6. Review the database stats, harvest status, and analysis results

The Python Analysis tool offers:
- **Cost Optimization**: Smart filtering reduces API costs
- **Sentiment Analysis**: Finds higher quality problems through emotional analysis
- **Temporal Patterns**: Analyzes when problems are posted for timing insights
- **User Behavior**: Tracks who posts problems and repeat patterns
- **Delta Harvesting**: Only fetch new content since last harvest (90-95% faster)
- **Database Storage**: Persistent SQLite storage with full-text search

## Production

Build the application for production:

```bash
# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.
