# Dashboard Screenshot Service Setup

This directory contains the Playwright script for server-side dashboard screenshot generation.

## Installation

### Step 1: Install Node.js and npm
Ensure Node.js (v14+) and npm are installed on your server.

### Step 2: Install Playwright
From the project root directory (`peakpulse/`), run:

```bash
npm init -y
npm install playwright
npx playwright install chromium
```

**Note:** Only Chromium is needed (lightweight and fast). The installation will download ~170MB.

### Step 3: Verify Installation
Test the script manually:

```bash
node scripts/capture_dashboard.js "http://localhost:8000/dashboard" test-output.png
```

If successful, you should see `test-output.png` created.

## How It Works

1. **React Frontend** → User clicks download button
2. **Django Backend** → Receives request at `/api/export/dashboard/`
3. **Playwright Script** → Launches headless Chromium, navigates to dashboard URL
4. **Screenshot** → Full-page screenshot captured (includes iframes, charts, maps)
5. **Response** → PNG/PDF file returned to user

## Security Features

- ✅ Authentication required (`@login_required`)
- ✅ URL whitelist validation (only same-origin URLs)
- ✅ Timeout protection (2 minute max)
- ✅ Error logging

## Troubleshooting

### "Playwright script not found"
- Ensure `scripts/capture_dashboard.js` exists
- Check file permissions

### "node: command not found"
- Install Node.js on your server
- Ensure `node` is in PATH

### "Failed to generate screenshot"
- Check Playwright installation: `npx playwright --version`
- Verify Chromium is installed: `npx playwright install chromium`
- Check server logs for detailed error messages

### Screenshot is blank or incomplete
- Increase wait time in `capture_dashboard.js` (line 47)
- Check if dashboard requires authentication (cookies are passed via Django session)

## Production Considerations

1. **Rate Limiting**: Consider adding rate limiting to prevent abuse
2. **File Cleanup**: Implement a cleanup task to remove old screenshot files
3. **Caching**: Consider caching screenshots for frequently accessed dashboards
4. **Queue System**: For high traffic, consider using Celery to queue screenshot generation

## File Cleanup (Optional)

Add to your Celery tasks or cron job:

```python
# Clean up screenshots older than 24 hours
import os
from datetime import datetime, timedelta
from django.conf import settings

def cleanup_old_screenshots():
    media_root = settings.MEDIA_ROOT
    cutoff = datetime.now() - timedelta(hours=24)
    
    for filename in os.listdir(media_root):
        if filename.startswith('dashboard-') and (filename.endswith('.png') or filename.endswith('.pdf')):
            filepath = os.path.join(media_root, filename)
            if os.path.getmtime(filepath) < cutoff.timestamp():
                os.remove(filepath)
```

