module.exports = {
  apps: [{
    name: 'spacex-backend',
    script: './start.sh',
    cwd: '/home/clawd/clawd/projects/spacex-orbital/backend',
    interpreter: '/bin/bash',
    max_restarts: 10,
    autorestart: true
  }]
}
