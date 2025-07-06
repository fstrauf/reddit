import { spawn } from 'child_process';
import path from 'path';

// Define the expected request body structure
interface RequestBody {
  subreddits: string[];
  mode?: 'basic' | 'full';
  max_problems?: number;
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<RequestBody>(event);
    
    // Validate request body
    if (!body || !body.subreddits || !Array.isArray(body.subreddits) || body.subreddits.length === 0) {
      return {
        success: false,
        error: 'No subreddits specified'
      };
    }
    
    // Build command arguments for Python analysis script
    const pythonAnalysisPath = path.join(process.cwd(), '..', 'python_analysis_reddit');
    const args = ['analyze_problems.py']; // Use analyze_problems.py directly to bypass dependency check
    
    // Add mode (default to basic for faster results)
    if (body.mode === 'full') {
      args.push('--enhanced');
    } else {
      args.push('--basic');
    }
    
    // Add max problems limit
    if (body.max_problems) {
      args.push('--max-problems', body.max_problems.toString());
    } else {
      args.push('--max-problems', '50'); // Default limit for faster processing
    }
    
    // Add appropriate cluster count (max clusters should be less than problems)
    args.push('--clusters', '5'); // Conservative cluster count for reliability
    
    // Use the virtual environment Python interpreter
    const venvPython = path.join(pythonAnalysisPath, 'venv', 'bin', 'python3');
    
    // Get runtime config for environment variables
    const config = useRuntimeConfig();
    
    // Prepare environment variables for Python script
    const env = {
      ...process.env,
      REDDIT_CLIENT_ID: config.redditClientId,
      REDDIT_CLIENT_SECRET: config.redditClientSecret,
      REDDIT_USER_AGENT: 'RedditAnalyzer/1.0',
      OPENAI_API_KEY: config.openaiApiKey
    };
    
    // Execute the command
    console.log(`Executing analysis: ${venvPython} ${args.join(' ')}`);
    
    // Use promise to handle async execution with timeout
    const output = await new Promise<string>((resolve, reject) => {
      const childProcess = spawn(venvPython, args, {
        cwd: pythonAnalysisPath,
        env: env
      });
      
      let stdout = '';
      let stderr = '';
      
      // Set a timeout for the process (2 minutes)
      const timeout = setTimeout(() => {
        childProcess.kill('SIGTERM');
        reject(new Error('Analysis timed out after 2 minutes'));
      }, 120000);
      
      childProcess.stdout.on('data', (data: Buffer) => {
        stdout += data.toString();
      });
      
      childProcess.stderr.on('data', (data: Buffer) => {
        stderr += data.toString();
      });
      
      childProcess.on('close', (code: number) => {
        clearTimeout(timeout);
        if (code === 0) {
          resolve(stdout);
        } else {
          const errorMsg = stderr || `Process exited with code ${code}`;
          console.error('Python analysis error:', errorMsg);
          console.error('Stdout:', stdout);
          reject(new Error(`Analysis failed: ${errorMsg}`));
        }
      });
      
      childProcess.on('error', (err: Error) => {
        clearTimeout(timeout);
        reject(err);
      });
    });
    
    // Read the generated JSON output file
    let analysisResults = null;
    try {
      const fs = await import('fs');
      const outputDir = path.join(pythonAnalysisPath, 'output');
      
      // Find the most recent analysis JSON file
      const files = fs.readdirSync(outputDir);
      const jsonFiles = files.filter(f => f.startsWith('enhanced_opportunities_') && f.endsWith('.json'));
      
      if (jsonFiles.length > 0) {
        // Sort by timestamp (filename contains timestamp)
        const latestFile = jsonFiles.sort().reverse()[0];
        const jsonPath = path.join(outputDir, latestFile);
        
        const jsonContent = fs.readFileSync(jsonPath, 'utf-8');
        analysisResults = JSON.parse(jsonContent);
      }
    } catch (jsonError) {
      console.warn('Could not read analysis JSON file:', jsonError);
    }
    
    return {
      success: true,
      output,
      results: analysisResults,
      subreddits: body.subreddits,
      mode: body.mode || 'basic'
    };
    
  } catch (error: any) {
    console.error('Error in python analysis:', error);
    
    return {
      success: false,
      error: error.message || 'Failed to execute analysis',
      output: error.message
    };
  }
}); 