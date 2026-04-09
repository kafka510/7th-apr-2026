import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type KpiSummaryCardTheme = 'blue' | 'amber' | 'emerald';

const themeStyles: Record<
  KpiSummaryCardTheme,
  {
    border: string;
    iconBg: string;
    iconColor: string;
    iconRing: string;
    hoverBg: string;
  }
> = {
  blue: {
    border: 'border-l-blue-500',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-700',
    iconRing: 'ring-2 ring-blue-200/80',
    hoverBg: 'hover:bg-blue-50/40',
  },
  amber: {
    border: 'border-l-amber-500',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-700',
    iconRing: 'ring-2 ring-amber-200/80',
    hoverBg: 'hover:bg-amber-50/40',
  },
  emerald: {
    border: 'border-l-emerald-500',
    iconBg: 'bg-emerald-100',
    iconColor: 'text-emerald-700',
    iconRing: 'ring-2 ring-emerald-200/80',
    hoverBg: 'hover:bg-emerald-50/40',
  },
};

interface KpiSummaryCardProps {
  theme: KpiSummaryCardTheme;
  title: string;
  icon: ReactNode;
  children: ReactNode;
  className?: string;
}

export function KpiSummaryCard({
  theme,
  title,
  icon,
  children,
  className,
}: KpiSummaryCardProps) {
  const styles = themeStyles[theme];
  return (
    <div
      className={cn(
        'group rounded-xl border border-gray-200 bg-white p-4 shadow-sm',
        'transition-all duration-200 ease-out',
        'hover:shadow-md hover:-translate-y-0.5 hover:border-gray-300',
        styles.hoverBg,
        'border-l-4',
        styles.border,
        className
      )}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-transform duration-200 group-hover:scale-105',
              styles.iconBg,
              styles.iconColor,
              styles.iconRing
            )}
          >
            {icon}
          </div>
          <h3 className="text-base font-semibold text-foreground tracking-tight">
            {title}
          </h3>
        </div>
        <div className="flex flex-col gap-2 min-h-[1.5rem]">
          {children}
        </div>
      </div>
    </div>
  );
}
