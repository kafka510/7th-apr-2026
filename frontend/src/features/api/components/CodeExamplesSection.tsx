/**
 * Code Examples Section Component
 */
 
interface CodeExamplesSectionProps {
  baseUrl: string;
}

export function CodeExamplesSection({ baseUrl }: CodeExamplesSectionProps) {
  return (
    <section id="code-examples" className="mb-5">
      <div className="card">
        <div className="card-header bg-success text-white">
          <h3 className="mb-0">
            Code Examples
          </h3>
        </div>
        <div className="card-body">
          <ul className="nav nav-tabs" id="codeExampleTabs" role="tablist">
            <li className="nav-item" role="presentation">
              <button className="nav-link active font-semibold text-slate-900" id="python-tab" data-bs-toggle="tab" data-bs-target="#python" type="button" role="tab">
                Python
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button className="nav-link font-semibold text-slate-900" id="curl-tab" data-bs-toggle="tab" data-bs-target="#curl" type="button" role="tab">
                cURL
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button className="nav-link font-semibold text-slate-900" id="javascript-tab" data-bs-toggle="tab" data-bs-target="#javascript" type="button" role="tab">
                JavaScript
              </button>
            </li>
          </ul>
          <div className="tab-content" id="codeExampleTabContent">
            {/* Python Example */}
            <div className="tab-pane fade show active" id="python" role="tabpanel">
              <pre className="bg-light mt-3 rounded p-3">
                <code className="font-mono font-semibold text-slate-900">
                  {`import requests

# Step 1: Get active token
api_key = "your-api-key-here"
token_response = requests.post(
    "${baseUrl}/api/v1/auth/token",
    json={
        "api_key": api_key,
        "lifetime_minutes": 60,
        "max_uses": 100
    }
)
token = token_response.json()["token"]

# Step 2: Fetch data
headers = {"X-API-Token": token}
response = requests.get(
    "${baseUrl}/api/v1/data/YieldData",
    headers=headers,
    params={"page": 1, "page_size": 10}
)
data = response.json()
print(data)`}
                </code>
              </pre>
            </div>

            {/* cURL Example */}
            <div className="tab-pane fade" id="curl" role="tabpanel">
              <pre className="bg-light mt-3 rounded p-3">
                <code className="font-mono font-semibold text-slate-900">
                  {`# Step 1: Get active token
curl -X POST ${baseUrl}/api/v1/auth/token \\
  -H "Content-Type: application/json" \\
  -d '{"api_key":"your-api-key-here","lifetime_minutes":60,"max_uses":100}'

# Step 2: Fetch data
curl -X GET "${baseUrl}/api/v1/data/YieldData?page=1&page_size=10" \\
  -H "X-API-Token: your-active-token-here"`}
                </code>
              </pre>
            </div>

            {/* JavaScript Example */}
            <div className="tab-pane fade" id="javascript" role="tabpanel">
              <pre className="bg-light mt-3 rounded p-3">
                <code className="font-mono font-semibold text-slate-900">
                  {`// Step 1: Get active token
const apiKey = "your-api-key-here";
const tokenResponse = await fetch("${baseUrl}/api/v1/auth/token", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
        api_key: apiKey,
        lifetime_minutes: 60,
        max_uses: 100
    })
});
const {token} = await tokenResponse.json();

// Step 2: Fetch data
const dataResponse = await fetch(
    \`${baseUrl}/api/v1/data/YieldData?page=1&page_size=10\`,
    {headers: {"X-API-Token": token}}
);
const data = await dataResponse.json();
console.log(data);`}
                </code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

