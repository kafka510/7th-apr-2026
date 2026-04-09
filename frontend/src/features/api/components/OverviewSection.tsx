/**
 * Overview Section Component
 */
 
export function OverviewSection() {
  return (
    <section id="overview" className="mb-5">
      <div className="card">
        <div className="card-header bg-success text-white">
          <h3 className="mb-0">
            Overview
          </h3>
        </div>
        <div className="card-body">
          <p className="font-medium text-slate-900">Welcome to the Peak Energy API! This documentation will help you integrate your systems with our API to access your data programmatically.</p>

          <h5 className="font-bold text-slate-900">What you can do with the API:</h5>
          <ul className="text-slate-900">
            <li className="font-medium">Retrieve data from authorized tables</li>
            <li className="font-medium">
              <strong className="font-bold">Advanced filtering</strong> with date ranges, text search, and numeric ranges
            </li>
            <li className="font-medium">Aggregate data for analytics</li>
            <li className="font-medium">Access real-time and historical data</li>
            <li className="font-medium">Combine multiple filters for complex queries</li>
          </ul>

          <div className="alert alert-info">
            <strong className="font-bold text-slate-900">
              Security:
            </strong>{' '}
            <span className="font-medium text-slate-900">All API requests are read-only and respect your hierarchical access permissions (countries, portfolios, sites).</span>
          </div>
        </div>
      </div>
    </section>
  );
}

