/**
 * Filtering Section Component
 */
 
export function FilteringSection() {
  return (
    <section id="advanced-filtering" className="mb-5">
      <div className="card">
        <div className="card-header bg-info text-white">
          <h3 className="mb-0">
            Advanced Filtering System
          </h3>
        </div>
        <div className="card-body">
          <div className="alert alert-success">
            <h5 className="alert-heading font-bold text-slate-900">
              New Feature: Intelligent Filtering
            </h5>
            <p className="mb-0 font-medium text-slate-900">
              The API now supports <strong className="font-bold">advanced filtering</strong> with automatic field type detection and multiple filter operators!
            </p>
          </div>

          <h5 className="font-bold text-slate-900">
            Date Range Filtering
          </h5>
          <p className="font-medium text-slate-900">Filter data by date ranges for DateTimeField and DateField columns:</p>

          <div className="row">
            <div className="col-md-6">
              <div className="card border-primary">
                <div className="card-header bg-primary text-white">
                  <strong>Date Range</strong>
                </div>
                <div className="card-body">
                  <pre className="bg-light mb-2 p-2">
                    <code className="font-mono font-semibold text-slate-900">
                      {`{"day_date": {
    "start": "2024-01-01",
    "end": "2024-12-31"
}}`}
                    </code>
                  </pre>
                  <small className="font-medium text-slate-700">Get records within date range</small>
                </div>
              </div>
            </div>
            <div className="col-md-6">
              <div className="card border-success">
                <div className="card-header bg-success text-white">
                  <strong>Text Search</strong>
                </div>
                <div className="card-body">
                  <pre className="bg-light mb-2 p-2">
                    <code className="font-mono font-semibold text-slate-900">{'{"asset_name": {"icontains": "solar"}}'}</code>
                  </pre>
                  <small className="font-medium text-slate-700">Case-insensitive contains</small>
                </div>
              </div>
            </div>
          </div>

          <h5 className="mt-4 font-bold text-slate-900">
            Numeric Range Filtering
          </h5>
          <p className="font-medium text-slate-900">Filter numeric fields with range operators:</p>

          <div className="row">
            <div className="col-md-6">
              <div className="card border-danger">
                <div className="card-header bg-danger text-white">
                  <strong>Min/Max Range</strong>
                </div>
                <div className="card-body">
                  <pre className="bg-light mb-2 p-2">
                    <code className="font-mono font-semibold text-slate-900">
                      {`{"daily_prod_rec": {
    "min": 100,
    "max": 1000
}}`}
                    </code>
                  </pre>
                  <small className="font-medium text-slate-700">Between min and max values</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

