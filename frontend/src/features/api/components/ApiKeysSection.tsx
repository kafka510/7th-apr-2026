/**
 * API Keys Section Component
 */
 
import type { APIKey } from '../types';

interface ApiKeysSectionProps {
  apiKeys: APIKey[];
}

export function ApiKeysSection({ apiKeys }: ApiKeysSectionProps) {
  return (
    <section id="api-keys" className="mb-5">
      <div className="card">
        <div className="card-header bg-dark text-white">
          <div className="d-flex justify-content-between align-items-center">
            <h3 className="mb-0">
              Your API Keys
            </h3>
            <a href="/api/dashboard/" className="btn btn-sm btn-light">
              Generate New Key
            </a>
          </div>
        </div>
        <div className="card-body">
          {apiKeys.length > 0 ? (
            <div className="table-responsive">
              <table className="table-hover table">
                <thead>
                  <tr>
                    <th className="font-bold text-slate-900">Name</th>
                    <th className="font-bold text-slate-900">Key Prefix</th>
                    <th className="font-bold text-slate-900">Status</th>
                    <th className="font-bold text-slate-900">Created</th>
                    <th className="font-bold text-slate-900">Expires</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((key) => (
                    <tr key={key.id}>
                      <td className="font-semibold text-slate-900">
                        <strong>{key.name}</strong>
                      </td>
                      <td className="text-slate-900">
                        <code className="font-mono font-semibold text-slate-900">{key.key_prefix}...</code>
                      </td>
                      <td className="text-slate-900">
                        {key.status === 'active' ? (
                          <span className="badge bg-success">Active</span>
                        ) : (
                          <span className="badge bg-secondary">{key.status}</span>
                        )}
                      </td>
                      <td className="text-slate-900">{key.created_at ? new Date(key.created_at).toLocaleDateString() : 'N/A'}</td>
                      <td className="text-slate-900">{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="alert alert-warning">
              <span className="font-medium text-slate-900">You don&apos;t have any API keys yet.{' '}</span>
              <a href="/api/dashboard/" className="alert-link font-semibold text-slate-900 underline">
                Generate your first API key
              </a>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

