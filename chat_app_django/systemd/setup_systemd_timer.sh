#!/bin/bash
# Setup script for the active fundamentals update systemd timer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - UPDATE THESE PATHS
PROJECT_DIR="/path/to/your/chat_app_server/chat_app_django"
VENV_DIR="/path/to/your/venv"
USER="www-data"
GROUP="www-data"

echo -e "${YELLOW}Setting up Active Stock Fundamentals Update Timer${NC}"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory $PROJECT_DIR does not exist${NC}"
    echo "Please update the PROJECT_DIR variable in this script"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment $VENV_DIR does not exist${NC}"
    echo "Please update the VENV_DIR variable in this script"
    exit 1
fi

echo -e "${YELLOW}1. Creating systemd service file...${NC}"
# Create the service file with correct paths
cat > /etc/systemd/system/update-fundamentals.service << EOF
[Unit]
Description=Update Active Stock Fundamentals
After=network.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
Group=$GROUP
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=chat_app_django.settings
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin

# Command to run
ExecStart=$VENV_DIR/bin/python manage.py update_active_fundamentals --rate-limit 250

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=update-fundamentals

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$PROJECT_DIR

# Restart policy for failures
Restart=no
RestartSec=30

# Timeout settings
TimeoutStartSec=600
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

echo -e "${YELLOW}2. Creating systemd timer file...${NC}"
# Create the timer file
cat > /etc/systemd/system/update-fundamentals.timer << EOF
[Unit]
Description=Run Active Stock Fundamentals Update Every Hour
Requires=update-fundamentals.service

[Timer]
# Run every hour at :05 past the hour (to avoid top-of-hour congestion)
OnCalendar=*-*-* *:05:00

# Run immediately if the system was off when the timer should have run
Persistent=yes

# Add some randomization to prevent all services starting at exactly the same time
RandomizedDelaySec=300

# Accuracy - how close to the scheduled time the timer should run
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

echo -e "${YELLOW}3. Reloading systemd daemon...${NC}"
systemctl daemon-reload

echo -e "${YELLOW}4. Enabling the timer...${NC}"
systemctl enable update-fundamentals.timer

echo -e "${YELLOW}5. Starting the timer...${NC}"
systemctl start update-fundamentals.timer

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Useful commands:"
echo "  Check timer status:    systemctl status update-fundamentals.timer"
echo "  Check service status:  systemctl status update-fundamentals.service"
echo "  View logs:             journalctl -u update-fundamentals.service -f"
echo "  Run manually:          systemctl start update-fundamentals.service"
echo "  List timers:           systemctl list-timers"
echo "  Stop timer:            systemctl stop update-fundamentals.timer"
echo "  Disable timer:         systemctl disable update-fundamentals.timer"
echo ""
echo -e "${YELLOW}Next run scheduled for: $(systemctl list-timers update-fundamentals.timer --no-pager | grep update-fundamentals | awk '{print $1, $2}')${NC}"

# Test the service
echo -e "${YELLOW}6. Testing the service (dry run)...${NC}"
echo "Running: $VENV_DIR/bin/python $PROJECT_DIR/manage.py update_active_fundamentals --dry-run"
cd "$PROJECT_DIR"
sudo -u "$USER" "$VENV_DIR/bin/python" manage.py update_active_fundamentals --dry-run

echo ""
echo -e "${GREEN}✓ Setup and test complete!${NC}"
echo "The timer will run every hour at :05 past the hour."