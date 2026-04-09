/**
 * API Manual/Documentation Page Component
 */
 
import { useState, useEffect } from 'react';
import { fetchAPIUserInfo, fetchAPIKeys } from './api';
import type { APIUserInfo, APIKey } from './types';
import { OverviewSection } from './components/OverviewSection';
import { AccessInfoSection } from './components/AccessInfoSection';
import { ApiKeysSection } from './components/ApiKeysSection';
import { AuthenticationSection } from './components/AuthenticationSection';
import { EndpointsSection } from './components/EndpointsSection';
import { FilteringSection } from './components/FilteringSection';
import { CodeExamplesSection } from './components/CodeExamplesSection';
import { RateLimitsSection } from './components/RateLimitsSection';
import { ErrorCodesSection } from './components/ErrorCodesSection';

// Get base URL from the page (passed from Django template)
function getBaseUrl(): string {
  if (typeof document === 'undefined') {
    return '';
  }
  const scriptTag = document.getElementById('api-base-url-data');
  if (scriptTag && scriptTag.textContent) {
    return scriptTag.textContent.trim();
  }
  return window.location.origin;
}

export function ApiManual() {
  const [userInfo, setUserInfo] = useState<APIUserInfo | null>(null);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [baseUrl, setBaseUrl] = useState<string>('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const base = getBaseUrl();
        setBaseUrl(base);
        
        const [userData, keysData] = await Promise.all([
          fetchAPIUserInfo(),
          fetchAPIKeys(),
        ]);
        
        setUserInfo(userData);
        setApiKeys(keysData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load API information');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-5">
        <div className="rounded-lg bg-white p-12 text-center shadow-md">
          <div className="mb-4 text-4xl text-blue-500">Loading...</div>
          <p className="text-lg text-slate-600">Loading API documentation...</p>
        </div>
      </div>
    );
  }

  if (error || !userInfo) {
    return (
      <div className="min-h-screen bg-slate-50 p-5">
        <div className="rounded-lg border border-red-400 bg-red-50 p-6 text-red-800">
          <strong>Error:</strong> {error || 'Failed to load API information'}
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col bg-slate-50" style={{ color: '#1e293b', minHeight: '100%' }}>
      <div className="flex-1">
      <div className="container-fluid mx-auto py-4">
        <div className="row">
          {/* Sidebar with Table of Contents */}
          <div className="col-md-3">
            <div className="card position-sticky" style={{ top: '80px' }}>
              <div className="card-header bg-primary text-white">
                <h5 className="mb-0 font-bold">
                  Contents
                </h5>
              </div>
              <div className="list-group list-group-flush">
                <a href="#overview" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Overview
                </a>
                <a href="#your-access" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Your Access
                </a>
                <a href="#api-keys" className="list-group-item list-group-item-action font-medium text-slate-900">
                  API Keys
                </a>
                <a href="#authentication" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Authentication
                </a>
                <a href="#endpoints" className="list-group-item list-group-item-action font-medium text-slate-900">
                  API Endpoints
                </a>
                <a href="#advanced-filtering" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Advanced Filtering
                </a>
                <a href="#code-examples" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Code Examples
                </a>
                <a href="#rate-limits" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Rate Limits
                </a>
                <a href="#errors" className="list-group-item list-group-item-action font-medium text-slate-900">
                  Error Codes
                </a>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="col-md-9">
            {/* Header */}
            <div className="mb-4">
              <h1 className="font-bold text-slate-900">
                API Documentation
              </h1>
              <p className="lead font-medium text-slate-900">Complete guide to accessing your data via API</p>

              {/* Access Level Info */}
              {userInfo.api_user.access_level === 'api_only' && (
                <div className="alert alert-info">
                  <span className="font-medium text-slate-900">
                    You have <strong className="font-bold">API-only access</strong>. This page is your main interface for accessing our services via API.
                  </span>
                </div>
              )}
              {userInfo.api_user.access_level === 'both' && (
                <div className="alert alert-success">
                  <span className="font-medium text-slate-900">
                    You have <strong className="font-bold">both web and API access</strong>. You can access the{' '}
                    <a href="/dashboard/" className="alert-link font-semibold text-slate-900 underline">
                      web dashboard
                    </a>{' '}
                    or use the API as documented here.
                  </span>
                </div>
              )}
            </div>

            {/* Sections */}
            <OverviewSection />
            <AccessInfoSection userInfo={userInfo} />
            <ApiKeysSection apiKeys={apiKeys} />
            <AuthenticationSection baseUrl={baseUrl} />
            <EndpointsSection baseUrl={baseUrl} />
            <FilteringSection />
            <CodeExamplesSection baseUrl={baseUrl} />
            <RateLimitsSection apiUser={userInfo.api_user} />
            <ErrorCodesSection />
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

