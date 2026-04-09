import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';

type RootContainer = HTMLElement & {
  __mainReactRoot?: ReturnType<typeof createRoot>;
};

const container = document.getElementById('react-root') as RootContainer | null;

if (container) {
  // Avoid duplicate mounts if this bundle executes more than once.
  const root = container.__mainReactRoot ?? createRoot(container);
  container.__mainReactRoot = root;
  try {
    root.render(<App />);
  } catch (err) {
    console.error('[main] root.render threw synchronously', err);
    throw err;
  }
} else {
  if (import.meta.env.DEV) {
    console.warn('React root element "#react-root" not found. React app was not mounted.');
  }
}
