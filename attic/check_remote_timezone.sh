#!/bin/bash
# Commands to run on remote server to check timezone

echo "Check timezone on remote server:"
echo "================================"
echo ""
echo "1. System timezone:"
echo "   timedatectl | grep 'Time zone'"
echo ""
echo "2. Python timezone:"
echo "   python3 -c \"import time; print('TZ:', time.tzname, 'Offset:', time.timezone)\""
echo ""
echo "3. Test datetime conversion:"
echo "   python3 -c \"from datetime import datetime; print('Epoch 1749884489064 ms converts to:', datetime.fromtimestamp(1749884489064/1000))\""
echo ""
echo "4. PostgreSQL timezone:"
echo "   psql -U postgres -d etrapdb -c 'SHOW timezone;'"
echo ""
echo "Run these commands on the remote server where CDC agent is running"