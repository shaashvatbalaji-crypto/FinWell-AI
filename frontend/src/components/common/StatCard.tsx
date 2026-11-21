import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { TiltCard } from '../3d/TiltCard';

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  isPositive?: boolean;
  subtitle?: string;
  icon: React.ReactNode;
  accentColor?: 'blue' | 'cyan' | 'violet' | 'emerald';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  isPositive = true,
  subtitle,
  icon,
  accentColor = 'blue',
}) => {
  const accentGlow = {
    blue: 'border-l-finwell-primary text-finwell-primary bg-finwell-primary/10',
    cyan: 'border-l-finwell-cyan text-finwell-cyan bg-finwell-cyan/10',
    violet: 'border-l-finwell-violet text-finwell-violet bg-finwell-violet/10',
    emerald: 'border-l-finwell-success text-finwell-success bg-finwell-success/10',
  };

  return (
    <TiltCard className="p-5 border-l-4 border-l-finwell-primary/80">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-finwell-muted uppercase tracking-wider">
            {title}
          </p>
          <h3 className="mt-2 text-2xl font-bold tracking-tight text-finwell-text">
            {value}
          </h3>
        </div>
        <div className={`rounded-xl p-2.5 ${accentGlow[accentColor]}`}>
          {icon}
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs">
        {change && (
          <span
            className={`inline-flex items-center font-semibold ${
              isPositive ? 'text-finwell-success' : 'text-finwell-danger'
            }`}
          >
            {isPositive ? (
              <ArrowUpRight className="mr-0.5 h-3.5 w-3.5" />
            ) : (
              <ArrowDownRight className="mr-0.5 h-3.5 w-3.5" />
            )}
            {change}
          </span>
        )}
        {subtitle && <span className="text-finwell-dim">{subtitle}</span>}
      </div>
    </TiltCard>
  );
};
