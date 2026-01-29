module.exports = {
  apps: [{
    name: 'spacex-backend',
    script: './start.sh',
    cwd: '/home/clawd/clawd/projects/spacex-orbital/backend',
    interpreter: '/bin/bash',
    
    // Stability
    max_restarts: 10,
    min_uptime: '10s',
    autorestart: true,
    restart_delay: 4000,
    
    // Memory management
    max_memory_restart: '500M',
    
    // Logging
    error_file: '/home/clawd/.pm2/logs/spacex-backend-error.log',
    out_file: '/home/clawd/.pm2/logs/spacex-backend-out.log',
    merge_logs: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    
    // Health check
    listen_timeout: 10000,
    kill_timeout: 5000,
    
    // Environment
    env: {
      NODE_ENV: 'production',
      REDIS_URL: 'redis://localhost:6379'
    }
  }]
}
