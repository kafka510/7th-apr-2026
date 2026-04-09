/**
 * Endpoints Section Component
 */
 
interface EndpointsSectionProps {
  baseUrl: string;
}

export function EndpointsSection({ baseUrl }: EndpointsSectionProps) {
  return (
    <section id="endpoints" className="mb-5">
      <div className="card">
        <div className="card-header bg-primary text-white">
          <h3 className="mb-0">
            API Endpoints
          </h3>
        </div>
        <div className="card-body">
          <h5 className="font-bold text-slate-900">Base URL</h5>
          <pre className="bg-light rounded p-3">
            <code className="font-mono font-semibold text-slate-900">{`${baseUrl}/api/v1/`}</code>
          </pre>

          <div className="alert alert-info mb-4">
            <strong className="font-bold text-slate-900">
              Automatic Data Filtering:
            </strong>
            <p className="mb-0 font-medium text-slate-900">All API responses are automatically filtered based on your access permissions:</p>
            <ul className="mb-0 text-slate-900">
              <li className="font-medium">
                <strong className="font-bold">Hierarchical Access</strong>: Data filtered by your accessible countries, portfolios, or sites
              </li>
              <li className="font-medium">
                <strong className="font-bold">Column Restrictions</strong>: Sensitive columns are automatically hidden or masked
              </li>
              <li className="font-medium">
                <strong className="font-bold">Read-Only</strong>: All endpoints are read-only - you cannot modify data
              </li>
            </ul>
          </div>

          <h5 className="mt-4 font-bold text-slate-900">Available Endpoints:</h5>

          <div className="accordion" id="endpointsAccordion">
            {/* Authentication */}
            <div className="accordion-item">
              <h2 className="accordion-header" id="headingAuth">
                <button className="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAuth">
                  <strong>1. Authentication Endpoint</strong>
                </button>
              </h2>
              <div id="collapseAuth" className="accordion-collapse show collapse" data-bs-parent="#endpointsAccordion">
                <div className="accordion-body">
                  <h6 className="font-bold text-slate-900">
                    <span className="badge bg-success">POST</span> Request Active Token
                  </h6>
                  <pre className="bg-light p-2">
                    <code className="font-mono font-semibold text-slate-900">POST /api/v1/auth/token</code>
                  </pre>
                </div>
              </div>
            </div>

            {/* Schema Discovery */}
            <div className="accordion-item">
              <h2 className="accordion-header" id="headingSchema">
                <button className="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSchema">
                  <strong>2. Schema Discovery Endpoints</strong>
                </button>
              </h2>
              <div id="collapseSchema" className="accordion-collapse collapse" data-bs-parent="#endpointsAccordion">
                <div className="accordion-body">
                  <h6 className="font-bold text-slate-900">
                    <span className="badge bg-primary">GET</span> List Available Tables
                  </h6>
                  <pre className="bg-light p-2">
                    <code className="font-mono font-semibold text-slate-900">GET /api/v1/schema/tables</code>
                  </pre>
                </div>
              </div>
            </div>

            {/* Data Access */}
            <div className="accordion-item">
              <h2 className="accordion-header" id="headingData">
                <button className="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseData">
                  <strong>3. Data Access Endpoints</strong>
                </button>
              </h2>
              <div className="accordion-collapse collapse" id="collapseData" data-bs-parent="#endpointsAccordion">
                <div className="accordion-body">
                  <h6 className="font-bold text-slate-900">
                    <span className="badge bg-primary">GET</span> Get Table Data
                  </h6>
                  <pre className="bg-light p-2">
                    <code className="font-mono font-semibold text-slate-900">GET /api/v1/data/{'{table_name}'}?page=1&page_size=100</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

