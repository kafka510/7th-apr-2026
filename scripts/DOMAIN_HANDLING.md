# Domain and Cookie Handling for Dashboard Screenshots

## How It Works

The screenshot service works for users accessing from **any IP address or domain** because cookies are matched based on the **URL domain**, not the user's IP address.

### Authentication Flow

1. **User accesses dashboard** (e.g., `https://app.example.com/unified-operations-dashboard/`)
   - Django sets session cookies with domain: `app.example.com`
   - User's browser stores cookies for this domain

2. **User clicks download**
   - React sends request to: `/api/export/dashboard/?url=https://app.example.com/unified-operations-dashboard/`
   - Django extracts **all cookies** from the authenticated request
   - Django passes cookies to Playwright script with domain matching the dashboard URL

3. **Playwright sets cookies**
   - Playwright navigates to: `https://app.example.com` (base domain)
   - Playwright sets cookies with domain: `app.example.com`
   - Playwright navigates to: `https://app.example.com/unified-operations-dashboard/`
   - Django sees the cookies → User is authenticated → Dashboard content is captured

### Domain Matching

The key is that **the domain from the dashboard URL matches the domain the user is accessing**:

- **Development (localhost)**: 
  - URL: `http://localhost:8000/unified-operations-dashboard/`
  - Domain: `localhost`
  - Cookies: No domain set (Playwright handles localhost automatically)

- **Production (domain name)**:
  - URL: `https://app.example.com/unified-operations-dashboard/`
  - Domain: `app.example.com`
  - Cookies: Domain set to `app.example.com`

- **Production (IP address)**:
  - URL: `http://192.168.1.100:8000/unified-operations-dashboard/`
  - Domain: `192.168.1.100`
  - Cookies: Domain set to `192.168.1.100`

### Why This Works for Different IPs

**Cookies are domain-based, not IP-based.** 

- User A accesses from `https://app.example.com` → Gets cookies for `app.example.com`
- User B accesses from `https://app.example.com` (different IP) → Gets cookies for `app.example.com`
- When Playwright captures: Uses domain `app.example.com` → Cookies match → Authentication works

The user's IP address doesn't matter because:
1. Django session cookies are set based on the **domain** in the request
2. The dashboard URL in the download request uses the same domain
3. Playwright sets cookies for that same domain
4. Django recognizes the cookies regardless of the IP that set them

### Important Notes

1. **URL must match user's domain**: The `url` parameter in the API call must use the same domain the user is accessing (not a different domain or localhost)

2. **Cookies are extracted from request**: The Django view extracts cookies from `request.COOKIES`, which contains the cookies from the user's authenticated session

3. **Domain from URL is used**: The domain extracted from `dashboard_url` is used to set cookies in Playwright, ensuring they match

### Troubleshooting

**Problem**: Screenshot shows login page instead of dashboard

**Solutions**:
- Check that the `url` parameter uses the same domain the user is accessing
- Verify cookies are being passed (check Django logs: "Extracted X cookies for domain Y")
- Check Playwright logs: "Setting X cookies for domain Y"
- Ensure the domain in the URL matches the domain where Django is running

**Problem**: Cookies fail to set in Playwright

**Solutions**:
- For localhost: This is handled automatically (domain is omitted)
- For production: Ensure domain matches exactly (e.g., `app.example.com` not `www.app.example.com`)
- Check that Playwright navigates to the base domain before setting cookies

