#!/usr/bin/env python3
"""
Web UI for Reddit Harvester
Simple Flask-based interface for configuring and running Reddit harvests
"""

import os
import json
import subprocess
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from harvest_reddit_enhanced import EnhancedRedditHarvester

app = Flask(__name__)

# Global variables to track harvest status
harvest_status = {
    'running': False,
    'progress': '',
    'results': None,
    'error': None
}

def load_config():
    """Load configuration and get available options"""
    try:
        harvester = EnhancedRedditHarvester()
        stats = harvester.get_stats() if harvester.use_database else None
        
        config = harvester.config
        preset_groups = config.get('subreddits', {}).get('preset_groups', {})
        
        return {
            'preset_groups': preset_groups,
            'stats': stats,
            'config': config
        }
    except Exception as e:
        return {
            'preset_groups': {},
            'stats': None,
            'config': {},
            'error': str(e)
        }

def run_harvest_command(params):
    """Run harvest command in background"""
    global harvest_status
    
    try:
        harvest_status['running'] = True
        harvest_status['progress'] = 'Starting harvest...'
        harvest_status['error'] = None
        
        # Build command
        cmd = ['python3', 'harvest_reddit_enhanced.py']
        
        # Add subreddits
        if params.get('subreddits'):
            cmd.extend(['--subreddits'] + params['subreddits'])
        
        # Add mode
        if params.get('mode') and params['mode'] != 'smart':
            cmd.extend(['--mode', params['mode']])
        
        # Add posts per sub
        if params.get('posts_per_sub'):
            cmd.extend(['--posts-per-sub', str(params['posts_per_sub'])])
        
        # Add no-database flag
        if params.get('no_database'):
            cmd.append('--no-database')
        
        # Add output name
        if params.get('output_name'):
            cmd.extend(['--output-name', params['output_name']])
        
        harvest_status['progress'] = f'Running: {" ".join(cmd)}'
        
        # Run command
        result = subprocess.run(
            cmd,
            cwd='/Users/fstrauf/01_code/reddit/python_analysis',
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        harvest_status['running'] = False
        
        if result.returncode == 0:
            harvest_status['progress'] = 'Harvest completed successfully!'
            harvest_status['results'] = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': True
            }
        else:
            harvest_status['progress'] = 'Harvest failed!'
            harvest_status['error'] = result.stderr or result.stdout
            harvest_status['results'] = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': False
            }
            
    except subprocess.TimeoutExpired:
        harvest_status['running'] = False
        harvest_status['progress'] = 'Harvest timed out!'
        harvest_status['error'] = 'Command timed out after 10 minutes'
    except Exception as e:
        harvest_status['running'] = False
        harvest_status['progress'] = 'Harvest error!'
        harvest_status['error'] = str(e)

@app.route('/')
def index():
    """Main UI page"""
    config_data = load_config()
    return render_template('index.html', config=config_data)

@app.route('/api/config')
def api_config():
    """Get current configuration"""
    return jsonify(load_config())

@app.route('/api/stats')
def api_stats():
    """Get database statistics"""
    try:
        harvester = EnhancedRedditHarvester()
        if harvester.use_database:
            stats = harvester.get_stats()
            return jsonify({'success': True, 'stats': stats})
        else:
            return jsonify({'success': False, 'error': 'Database not enabled'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/harvest', methods=['POST'])
def api_harvest():
    """Start a harvest with given parameters"""
    global harvest_status
    
    if harvest_status['running']:
        return jsonify({'success': False, 'error': 'Harvest already running'})
    
    try:
        data = request.get_json()
        
        # Validate subreddits
        subreddits = data.get('subreddits', [])
        if not subreddits:
            return jsonify({'success': False, 'error': 'No subreddits specified'})
        
        # Parse parameters
        params = {
            'subreddits': subreddits,
            'mode': data.get('mode', 'smart'),
            'posts_per_sub': data.get('posts_per_sub'),
            'no_database': data.get('no_database', False),
            'output_name': data.get('output_name')
        }
        
        # Start harvest in background thread
        thread = threading.Thread(target=run_harvest_command, args=(params,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Harvest started'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def api_status():
    """Get current harvest status"""
    return jsonify(harvest_status)

@app.route('/api/reset-checkpoint', methods=['POST'])
def api_reset_checkpoint():
    """Reset checkpoint for a subreddit"""
    try:
        data = request.get_json()
        subreddit = data.get('subreddit')
        
        if not subreddit:
            return jsonify({'success': False, 'error': 'No subreddit specified'})
        
        # Run reset command
        cmd = ['python3', 'harvest_reddit_enhanced.py', '--reset-checkpoint', subreddit]
        result = subprocess.run(
            cmd,
            cwd='/Users/fstrauf/01_code/reddit/python_analysis',
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': f'Reset checkpoint for r/{subreddit}'})
        else:
            return jsonify({'success': False, 'error': result.stderr or result.stdout})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 Starting Reddit Harvester Web UI...")
    print("📱 Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
