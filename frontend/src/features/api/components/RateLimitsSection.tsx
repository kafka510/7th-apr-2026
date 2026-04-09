/**
 * Rate Limits Section Component
 */
 
import type { APIUser } from '../types';

interface RateLimitsSectionProps {
  apiUser: APIUser;
}

export function RateLimitsSection({ apiUser }: RateLimitsSectionProps) {
  return (
    <section id="rate-limits" className="mb-5">
      <div className="card">
        <div className="card-header bg-warning text-dark">
          <h3 className="mb-0">
            Rate Limits
          </h3>
        </div>
        <div className="card-body">
          <p className="font-medium text-slate-900">Your current rate limits:</p>
          <div className="row">
            <div className="col-md-4">
              <div className="rounded border p-3 text-center">
                <h4 className="text-primary font-bold">{apiUser.rate_limit_per_minute}</h4>
                <p className="mb-0 font-medium text-slate-700">Requests per Minute</p>
              </div>
            </div>
            <div className="col-md-4">
              <div className="rounded border p-3 text-center">
                <h4 className="text-success font-bold">{apiUser.rate_limit_per_hour}</h4>
                <p className="mb-0 font-medium text-slate-700">Requests per Hour</p>
              </div>
            </div>
            <div className="col-md-4">
              <div className="rounded border p-3 text-center">
                <h4 className="text-warning font-bold">{apiUser.rate_limit_per_day}</h4>
                <p className="mb-0 font-medium text-slate-700">Requests per Day</p>
              </div>
            </div>
          </div>
          <div className="alert alert-info mt-3">
            <span className="font-medium text-slate-900">If you exceed these limits, you&apos;ll receive a 429 (Too Many Requests) response. Wait before retrying.</span>
          </div>
        </div>
      </div>
    </section>
  );
}

