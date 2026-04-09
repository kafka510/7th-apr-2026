import { Button } from './Button';
import '../index.css';

type User = {
  name: string;
};

export interface HeaderProps {
  user?: User;
  onLogin?: () => void;
  onLogout?: () => void;
  onCreateAccount?: () => void;
}

export const Header = ({ user, onLogin, onLogout, onCreateAccount }: HeaderProps) => (
  <header className="border-b border-slate-800 bg-slate-900/80">
    <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-lg border border-sky-400/30 bg-sky-500/10 text-lg font-semibold text-sky-300">
          PE
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-100">Peak Energy</h1>
          <p className="text-xs text-slate-400">Unified operations dashboard</p>
        </div>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-300">
        {user ? (
          <>
            <span className="hidden sm:inline">
              Welcome, <b>{user.name}</b>!
            </span>
            <Button size="small" onClick={onLogout} label="Log out" />
          </>
        ) : (
          <>
            <Button size="small" onClick={onLogin} label="Log in" />
            <Button primary size="small" onClick={onCreateAccount} label="Sign up" />
          </>
        )}
      </div>
    </div>
  </header>
);
