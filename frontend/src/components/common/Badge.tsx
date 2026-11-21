import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'cyan' | 'violet' | 'success' | 'warning' | 'danger' | 'neutral';
  size?: 'sm' | 'md';
  className?: string;
  glow?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  glow = false,
}) => {
  const variantStyles = {
    primary: 'bg-finwell-primary/15 text-finwell-primary border-finwell-primary/30',
    cyan: 'bg-finwell-cyan/15 text-finwell-cyan border-finwell-cyan/30',
    violet: 'bg-finwell-violet/15 text-finwell-violet border-finwell-violet/30',
    success: 'bg-finwell-success/15 text-finwell-success border-finwell-success/30',
    warning: 'bg-finwell-warning/15 text-finwell-warning border-finwell-warning/30',
    danger: 'bg-finwell-danger/15 text-finwell-danger border-finwell-danger/30',
    neutral: 'bg-white/5 text-finwell-muted border-white/10',
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 rounded-full',
    md: 'text-xs px-2.5 py-1 rounded-full font-medium',
  };

  const glowStyles = glow ? 'shadow-[0_0_12px_rgba(66,99,255,0.25)]' : '';

  return (
    <span
      className={`inline-flex items-center gap-1.5 border transition-colors ${variantStyles[variant]} ${sizeStyles[size]} ${glowStyles} ${className}`}
    >
      {children}
    </span>
  );
};
