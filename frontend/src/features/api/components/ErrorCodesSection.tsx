/**
 * Error Codes Section Component
 */
 
export function ErrorCodesSection() {
  return (
    <section id="errors" className="mb-5">
      <div className="card">
        <div className="card-header bg-danger text-white">
          <h3 className="mb-0">
            Error Codes
          </h3>
        </div>
        <div className="card-body">
          <table className="table-striped table">
            <thead>
              <tr>
                <th className="font-bold text-slate-900">Code</th>
                <th className="font-bold text-slate-900">Message</th>
                <th className="font-bold text-slate-900">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="text-slate-900">
                  <code className="font-mono font-semibold text-slate-900">401</code>
                </td>
                <td className="font-semibold text-slate-900">Unauthorized</td>
                <td className="text-slate-900">Invalid or missing API credentials</td>
              </tr>
              <tr>
                <td className="text-slate-900">
                  <code className="font-mono font-semibold text-slate-900">403</code>
                </td>
                <td className="font-semibold text-slate-900">Forbidden</td>
                <td className="text-slate-900">You don&apos;t have permission to access this resource</td>
              </tr>
              <tr>
                <td className="text-slate-900">
                  <code className="font-mono font-semibold text-slate-900">404</code>
                </td>
                <td className="font-semibold text-slate-900">Not Found</td>
                <td className="text-slate-900">The requested resource doesn&apos;t exist</td>
              </tr>
              <tr>
                <td className="text-slate-900">
                  <code className="font-mono font-semibold text-slate-900">429</code>
                </td>
                <td className="font-semibold text-slate-900">Too Many Requests</td>
                <td className="text-slate-900">Rate limit exceeded</td>
              </tr>
              <tr>
                <td className="text-slate-900">
                  <code className="font-mono font-semibold text-slate-900">500</code>
                </td>
                <td className="font-semibold text-slate-900">Internal Server Error</td>
                <td className="text-slate-900">Something went wrong on our end</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

