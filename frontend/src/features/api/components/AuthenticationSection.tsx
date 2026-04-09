/**
 * Authentication Section Component
 */
 
interface AuthenticationSectionProps {
  baseUrl: string;
}

export function AuthenticationSection({ baseUrl }: AuthenticationSectionProps) {
  return (
    <section id="authentication" className="mb-5">
      <div className="card">
        <div className="card-header bg-warning text-dark">
          <h3 className="mb-0">
            Authentication
          </h3>
        </div>
        <div className="card-body">
          <div className="alert alert-primary">
            <h5 className="alert-heading font-bold text-slate-900">
              Two-Tier Authentication System
            </h5>
            <p className="mb-0 font-medium text-slate-900">Our API uses a secure two-tier authentication system:</p>
            <ol className="mb-0 mt-2 text-slate-900">
              <li className="font-medium">
                <strong className="font-bold">API Key</strong> (long-lived, secret) → Request token
              </li>
              <li className="font-medium">
                <strong className="font-bold">Active Token</strong> (short-lived, disposable) → Make requests
              </li>
            </ol>
          </div>

          <h5 className="mt-4 font-bold text-slate-900">
            Step 1: Request an Active Token
          </h5>
          <p className="font-medium text-slate-900">Use your API key to request an active token:</p>

          <div className="card mb-3">
            <div className="card-header bg-light">
              <strong>Request:</strong>
            </div>
            <div className="card-body">
              <pre className="bg-light mb-0 rounded p-3">
                <code>
                  {`POST ${baseUrl}/api/v1/auth/token
Content-Type: application/json

{
    "api_key": "your-api-key-here",
    "lifetime_minutes": 60,      // Optional: 1-1440 (1 min to 24 hours)
    "max_uses": 100              // Optional: 1-10000 requests
}`}
                </code>
              </pre>
            </div>
          </div>

          <div className="card mb-3">
            <div className="card-header bg-success text-white">
              <strong>Response:</strong>
            </div>
            <div className="card-body">
              <pre className="bg-light mb-0 rounded p-3">
                <code>
                  {`{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2025-10-20T11:00:00Z",
    "lifetime_minutes": 60,
    "max_uses": 100,
    "created_at": "2025-10-20T10:00:00Z"
}`}
                </code>
              </pre>
            </div>
          </div>

          <h5 className="mt-4 font-bold text-slate-900">
            Step 2: Use the Token for API Calls
          </h5>
          <p className="font-medium text-slate-900">Include the token in the <code className="font-mono font-semibold text-slate-900">X-API-Token</code> header for all data requests:</p>

          <div className="card mb-3">
            <div className="card-header bg-light">
              <strong>Request:</strong>
            </div>
            <div className="card-body">
              <pre className="bg-light mb-0 rounded p-3">
                <code>
                  {`GET ${baseUrl}/api/v1/data/YieldData?page=1&page_size=10
X-API-Token: your-active-token-here`}
                </code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

