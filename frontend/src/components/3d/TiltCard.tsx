import React, { useRef, useState } from 'react';

interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;
  glowEffect?: boolean;
}

export const TiltCard: React.FC<TiltCardProps> = ({
  children,
  className = '',
  maxTilt = 7,
  glowEffect = true,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const [glowPos, setGlowPos] = useState({ x: 50, y: 50 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const percentX = x / rect.width;
    const percentY = y / rect.height;

    const rotX = (percentY - 0.5) * -maxTilt;
    const rotY = (percentX - 0.5) * maxTilt;

    setRotation({ x: rotX, y: rotY });
    setGlowPos({ x: percentX * 100, y: percentY * 100 });
  };

  const handleMouseEnter = () => setIsHovered(true);
  const handleMouseLeave = () => {
    setIsHovered(false);
    setRotation({ x: 0, y: 0 });
  };

  return (
    <div
      style={{ perspective: '1000px' }}
      className="transition-transform duration-200"
    >
      <div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{
          transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
          transition: isHovered ? 'transform 0.08s ease-out' : 'transform 0.5s ease-out',
        }}
        className={`relative overflow-hidden rounded-2xl border border-white/[0.08] bg-finwell-card transition-all duration-300 ${
          isHovered ? 'border-finwell-primary/40 shadow-glow-sm' : ''
        } ${className}`}
      >
        {glowEffect && isHovered && (
          <div
            className="pointer-events-none absolute -inset-px opacity-40 transition-opacity duration-300"
            style={{
              background: `radial-gradient(400px circle at ${glowPos.x}% ${glowPos.y}%, rgba(66, 99, 255, 0.25), transparent 40%)`,
            }}
          />
        )}
        <div className="relative z-10">{children}</div>
      </div>
    </div>
  );
};
