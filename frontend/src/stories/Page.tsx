import { useState } from 'react';

import { Header } from './Header';
import '../index.css';

type User = {
  name: string;
};

export const Page = () => {
  const [user, setUser] = useState<User>();

  return (
    <article className="min-h-screen bg-slate-950 text-slate-100">
      <Header
        user={user}
        onLogin={() => setUser({ name: 'Jane Doe' })}
        onLogout={() => setUser(undefined)}
        onCreateAccount={() => setUser({ name: 'Jane Doe' })}
      />

      <section className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10">
        <h2 className="text-2xl font-semibold text-white">React Migration Overview</h2>
        <p className="text-sm leading-relaxed text-slate-300">
          The React migration adopts a component-driven process: begin with primitives, compose
          feature modules, and integrate them into Django. Storybook lets us preview realistic states
          before connecting to live data.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow shadow-slate-950/40">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-sky-400">
              Migration steps
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              <li>• Scaffold Vite + Tailwind foundation</li>
              <li>• Integrate DRF endpoints & typed contracts</li>
              <li>• Roll out React pages with feature flags</li>
            </ul>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow shadow-slate-950/40">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-sky-400">
              Storybook usage
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              <li>• Prototype dashboard components</li>
              <li>• Run accessibility & interaction tests</li>
              <li>• Collaborate with design on branding</li>
            </ul>
          </div>
        </div>
      </section>
    </article>
  );
};
