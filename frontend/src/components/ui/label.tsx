import * as React from 'react';
import * as LabelPrimitive from '@radix-ui/react-label';
import { cn } from '../../lib/utils';
import { useTheme } from '../../contexts/ThemeContext';

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  return (
    <LabelPrimitive.Root
      ref={ref}
      className={cn(
        'text-xs font-semibold',
        className
      )}
      style={{ color: isDark ? '#cbd5e1' : '#475569' }}
      {...props}
    />
  );
});
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };

