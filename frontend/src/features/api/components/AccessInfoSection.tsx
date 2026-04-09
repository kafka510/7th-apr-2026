/**
 * Access Info Section Component
 */
 
import type { APIUserInfo } from '../types';

interface AccessInfoSectionProps {
  userInfo: APIUserInfo;
}

export function AccessInfoSection({ userInfo }: AccessInfoSectionProps) {
  return (
    <section id="your-access" className="mb-5">
      <div className="card">
        <div className="card-header bg-info text-white">
          <h3 className="mb-0">
            Your Access
          </h3>
        </div>
        <div className="card-body">
          <div className="row">
            <div className="col-md-6">
              <h5 className="font-bold text-slate-900">User Information:</h5>
              <table className="table-sm table">
                <tbody>
                  <tr>
                    <th style={{ width: '40%' }} className="font-semibold text-slate-900">Access Level:</th>
                    <td className="text-slate-900">
                      <span className="badge bg-primary">{userInfo.api_user.access_level_display}</span>
                    </td>
                  </tr>
                  <tr>
                    <th className="font-semibold text-slate-900">Status:</th>
                    <td className="text-slate-900">
                      <span className={`badge ${userInfo.api_user.status === 'active' ? 'bg-success' : 'bg-secondary'}`}>
                        {userInfo.api_user.status}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="col-md-6">
              <h5 className="font-bold text-slate-900">Data Access:</h5>
              {userInfo.accessible_countries.length > 0 && (
                <p className="text-slate-900">
                  <strong className="font-semibold">Countries:</strong> {userInfo.accessible_countries.join(', ')}
                </p>
              )}
              {userInfo.accessible_portfolios.length > 0 && (
                <p className="text-slate-900">
                  <strong className="font-semibold">Portfolios:</strong> {userInfo.accessible_portfolios.join(', ')}
                </p>
              )}
              {userInfo.accessible_sites_count > 0 && (
                <p className="text-slate-900">
                  <strong className="font-semibold">Sites:</strong> {userInfo.accessible_sites_count} site(s)
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

