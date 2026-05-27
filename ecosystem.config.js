// PM2 process config for Career Revolution
// Start with:  pm2 start ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'career-revolution',
      script: 'run.py',
      interpreter: '.venv/bin/python3',
      cwd: '/opt/career-revolution',
      env: {
        BACKEND_PORT: '8010',
      },
      // Restart on crash, not on memory limit exceeded
      max_restarts: 10,
      restart_delay: 3000,
      // Log config
      out_file: 'logs/app.out.log',
      error_file: 'logs/app.err.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
    },
  ],
};
