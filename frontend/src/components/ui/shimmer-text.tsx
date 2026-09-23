import type { CSSProperties, ReactNode } from 'react';
import { cn } from '../../lib/utils';

interface TextShimmerProps {
  children: ReactNode;
  className?: string;
  duration?: number;
}

/** Lightweight text-only loading treatment with a reduced-motion fallback. */
export function TextShimmer({ children, className, duration = 2.4 }: TextShimmerProps) {
  const style = {
    '--text-shimmer-duration': `${duration}s`,
  } as CSSProperties;

  return (
    <span className={cn('text-shimmer', className)} style={style}>
      {children}
    </span>
  );
}
