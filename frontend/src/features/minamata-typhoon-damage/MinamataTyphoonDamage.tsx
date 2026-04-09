import { useEffect, useState } from 'react';
import { MinamataTable } from './components/MinamataTable';
import { useMinamataData } from './hooks/useMinamataData';

function getBigFont(base = 12, max = 18, min = 9): number {
  const width = window.innerWidth;
  return Math.max(min, Math.min(max, Math.round(base * (width / 1920))));
}

export function MinamataTyphoonDamage() {
  const { tableRows, loading, error } = useMinamataData();
  const [fontSize, setFontSize] = useState(getBigFont(12, 18, 9));

  useEffect(() => {
    const updateFontSize = () => {
      setFontSize(getBigFont(12, 18, 9));
    };
    
    window.addEventListener('resize', updateFontSize);
    return () => window.removeEventListener('resize', updateFontSize);
  }, []);

  // Ensure the component fills the viewport, especially in iframes
  useEffect(() => {
    const root = document.getElementById('react-root');
    if (root) {
      const setHeight = () => {
        if (window.self !== window.top) {
          root.style.height = '100%';
          root.style.minHeight = '100vh';
        } else {
          root.style.height = '100vh';
          root.style.minHeight = '100vh';
        }
      };

      setHeight();
      window.addEventListener('resize', setHeight);
      return () => window.removeEventListener('resize', setHeight);
    }
  }, []);

  if (error) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#c62828' }}>
        <h2>Error loading data</h2>
        <p>{error.message}</p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        margin: 0,
        padding: 0,
        background: '#f5f7fa',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '6px 16px 4px 16px',
          background: 'linear-gradient(135deg, rgba(10,115,209,0.12), rgba(16,185,129,0.12))',
          boxShadow: '0 8px 24px rgba(0,0,0,0.06)',
          borderRadius: '0 0 24px 24px',
          marginBottom: '4px',
          position: 'sticky',
          top: 0,
          zIndex: 10,
          backdropFilter: 'blur(12px)',
        }}
      >
        <h1
          style={{
            fontSize: `${getBigFont(16, 26, 10)}px`,
            fontWeight: 700,
            letterSpacing: '1px',
            margin: 0,
            display: 'block',
            textAlign: 'center',
            width: '100%',
            background: 'linear-gradient(90deg, #0a73d1, #10b981)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
          }}
        >
          Minamata - Gen Loss due to typhoon module damage
        </h1>
      </div>

      {/* Main Container */}
      <div
        style={{
          background: '#fff',
          borderRadius: '0 0 10px 10px',
          border: '1.5px solid #b2d8fc',
          boxShadow: '0 2px 10px rgba(99,171,221,0.07)',
          margin: '0 8px 8px 8px',
          padding: '0.8rem 1.2rem 0.2rem 1.2rem',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {/* Table */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <MinamataTable rows={tableRows} loading={loading} />
        </div>

        {/* Note Box */}
        <div
          style={{
            background: '#b2d8fc',
            borderRadius: '10px',
            color: '#123155',
            padding: '0.6rem 1.2rem',
            marginTop: '0.1rem',
            fontSize: `${fontSize}px`,
            minHeight: '50px',
            flexShrink: 0,
          }}
        >
          <b>Note:</b>
          <br />
          1.*Jan-25-July-25 : Actual breakdown & revenue losses are considered. July-25 to Dec-25: Expected losses are considered as per budgeted. Breakdown capacity: 3.82 MWp.
        </div>
      </div>
    </div>
  );
}

