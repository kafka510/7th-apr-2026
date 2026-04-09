import '../index.css';

export interface ButtonProps {
  /** Is this the principal call to action on the page? */
  primary?: boolean;
  /** What background color to use */
  backgroundColor?: string;
  /** How large should the button be? */
  size?: 'small' | 'medium' | 'large';
  /** Button contents */
  label: string;
  /** Optional click handler */
  onClick?: () => void;
}

/** Primary UI component for user interaction */
export const Button = ({
  primary = false,
  size = 'medium',
  backgroundColor,
  label,
  ...props
}: ButtonProps) => {
  const sizeClass =
    size === 'large' ? 'px-5 py-3 text-base' : size === 'small' ? 'px-3 py-2 text-xs' : 'px-4 py-2';

  return (
    <button
      type="button"
      className={[
        'inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-sm font-medium text-slate-100 shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/80 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950',
        primary ? 'bg-sky-500 text-white hover:bg-sky-400' : 'hover:bg-slate-800',
        sizeClass,
      ].join(' ')}
      style={{ backgroundColor }}
      {...props}
    >
      {label}
    </button>
  );
};
