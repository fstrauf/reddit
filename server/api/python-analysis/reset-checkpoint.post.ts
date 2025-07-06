import { spawn } from 'child_process';
import path from 'path';

// Define the expected request body structure
interface RequestBody {
  subreddit: string;
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<RequestBody>(event);
    
    // Validate request body
    if (!body || !body.subreddit) {
      return {
        success: false,
        error: 'No subreddit specified'
      };
    }
    
    const subreddit = body.subreddit.trim();
    
    // Build command arguments - updated path to new location
    const pythonAnalysisPath = path.join(process.cwd(), '..', 'python_analysis_reddit');
    const args = [
      path.join(pythonAnalysisPath, 'harvest_reddit_enhanced.py'),
      '--reset-checkpoint',
      subreddit
    ];
    
    // Use the virtual environment Python interpreter
    const venvPython = path.join(pythonAnalysisPath, 'venv', 'bin', 'python3');
    
    // Execute the command
    console.log(`Executing: ${venvPython} ${args.join(' ')}`);
    
    // Get runtime config for environment variables
    const config = useRuntimeConfig();
    
    // Prepare environment variables for Python script
    const env = {
      ...process.env,
      NUXT_REDDIT_CLIENT_ID: config.redditClientId,
      NUXT_REDDIT_CLIENT_SECRET: config.redditClientSecret,
      REDDIT_USER_AGENT: 'RedditAnalyzer/1.0',
      OPENAI_API_KEY: config.openaiApiKey
    };
    
    // Use promise to handle async execution
    const output = await new Promise<string>((resolve, reject) => {
      const childProcess = spawn(venvPython, args, {
        cwd: pythonAnalysisPath,
        env: env
      });
      
      let stdout = '';
      let stderr = '';
      
      childProcess.stdout.on('data', (data: Buffer) => {
        stdout += data.toString();
      });
      
      childProcess.stderr.on('data', (data: Buffer) => {
        stderr += data.toString();
      });
      
      childProcess.on('close', (code: number) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(stderr || `Process exited with code ${code}`));
        }
      });
      
      childProcess.on('error', (err: Error) => {
        reject(err);
      });
    });
    
    return {
      success: true,
      message: `Reset checkpoint for r/${subreddit}`,
      output
    };
    
  } catch (error: any) {
    console.error('Error resetting checkpoint:', error);
    
    return {
      success: false,
      error: error.message || 'Failed to reset checkpoint',
      output: error.message
    };
  }
});