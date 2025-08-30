# Active Stock Fundamentals Update - Systemd Timer

This directory contains the systemd service and timer configuration for automatically updating stock fundamentals for securities that users actively hold or watch.

## Overview

The system runs every hour and updates only the securities that appear in:
- User Holdings
- User Watchlists

This is much more efficient than updating all 8,532 securities, typically updating only 50-500 securities per run.

## Files

- `update-fundamentals.service` - Systemd service definition
- `update-fundamentals.timer` - Systemd timer definition (runs every hour at :05 past the hour)
- `setup_systemd_timer.sh` - Automated setup script
- `README.md` - This documentation

## Quick Setup

1. **Edit the setup script** with your actual paths:
   ```bash
   nano setup_systemd_timer.sh
   # Update these variables:
   PROJECT_DIR="/path/to/your/chat_app_server/chat_app_django"
   VENV_DIR="/path/to/your/venv"
   USER="your-django-user"
   GROUP="your-django-group"
   ```

2. **Run the setup script as root**:
   ```bash
   sudo ./setup_systemd_timer.sh
   ```

The setup script will:
- Create the service and timer files in `/etc/systemd/system/`
- Enable and start the timer
- Run a test to verify everything works

## Manual Setup

If you prefer manual setup:

1. **Copy and edit the service file**:
   ```bash
   sudo cp update-fundamentals.service /etc/systemd/system/
   sudo nano /etc/systemd/system/update-fundamentals.service
   # Update paths and user/group
   ```

2. **Copy the timer file**:
   ```bash
   sudo cp update-fundamentals.timer /etc/systemd/system/
   ```

3. **Enable and start**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable update-fundamentals.timer
   sudo systemctl start update-fundamentals.timer
   ```

## Management Commands

### Check Status
```bash
# Check if timer is running
systemctl status update-fundamentals.timer

# Check last service run
systemctl status update-fundamentals.service

# List all timers (shows next run time)
systemctl list-timers
```

### View Logs
```bash
# Follow logs in real-time
journalctl -u update-fundamentals.service -f

# View recent logs
journalctl -u update-fundamentals.service --since "1 hour ago"

# View all logs for the service
journalctl -u update-fundamentals.service
```

### Manual Execution
```bash
# Run the update immediately
systemctl start update-fundamentals.service

# Run with dry-run for testing
cd /path/to/your/project
python manage.py update_active_fundamentals --dry-run --verbose
```

### Stop/Disable
```bash
# Stop the timer
systemctl stop update-fundamentals.timer

# Disable the timer (prevents auto-start on boot)
systemctl disable update-fundamentals.timer

# Re-enable after changes
systemctl enable update-fundamentals.timer
systemctl start update-fundamentals.timer
```

## Schedule Details

- **Frequency**: Every hour
- **Time**: :05 past the hour (e.g., 1:05, 2:05, 3:05...)
- **Randomization**: Up to 5 minutes delay to prevent system congestion
- **Persistent**: Will run missed jobs if system was offline

## Rate Limiting

The service is configured to use 250 API calls per minute, which is below the FMP limit of 300/minute, leaving headroom for other API usage.

For a typical user base with ~100 active securities:
- **API calls needed**: ~100 calls
- **Time to complete**: ~25 seconds
- **Buffer for growth**: Can handle up to ~375 active securities per hour

## Monitoring

### Success Indicators
- Timer shows "PASSED" status: `systemctl list-timers`
- Service logs show completion: `journalctl -u update-fundamentals.service --since "1 hour ago"`
- No ERROR entries in logs

### Troubleshooting
- **Service fails to start**: Check paths and permissions in service file
- **API errors**: Check FMP API key and rate limiting
- **Database errors**: Verify Django settings and database connectivity
- **Permission errors**: Ensure service user has proper access to project files

## Customization

You can modify the update frequency by editing the timer file:

```ini
# Every 30 minutes
OnCalendar=*:00,30

# Every 2 hours
OnCalendar=*-*-* */2:05:00

# Only during market hours (9 AM - 5 PM EST, weekdays)
OnCalendar=Mon..Fri *-*-* 09,10,11,12,13,14,15,16,17:05:00
```

After changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart update-fundamentals.timer
```

## Production Considerations

- Monitor disk space for log files
- Consider log rotation for the Django application logs
- Set up alerting for service failures
- Monitor API usage to ensure you stay within FMP limits
- Consider scaling to multiple servers with database-level coordination