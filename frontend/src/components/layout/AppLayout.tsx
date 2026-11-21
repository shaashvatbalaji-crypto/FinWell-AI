import React, { useState } from 'react';
import { LeftSidebar, NavigationPage } from './LeftSidebar';
import { MiddleSidebar } from './MiddleSidebar';
import { DemoBanner } from '../common/DemoBanner';
import { BackgroundParticles3D } from '../3d/BackgroundParticles3D';
import { Menu, MessageSquare, Sparkles } from 'lucide-react';

interface AppLayoutProps {
  currentPage: NavigationPage;
  onSelectPage: (page: NavigationPage) => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPage,
  onSelectPage,
  children,
}) => {
  const [isLeftCollapsed, setIsLeftCollapsed] = useState<boolean>(false);
  const [isMiddleOpen, setIsMiddleOpen] = useState<boolean>(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // In AI Chat page, Middle Sidebar is essential and prominent
  const showMiddleSidebar = isMiddleOpen || currentPage === 'ai-chat';

  return (
    <div className="relative min-h-screen bg-finwell-bg text-finwell-text flex flex-col overflow-x-hidden">
      {/* Ambient 3D Particle Canvas */}
      <BackgroundParticles3D />

      {/* Top Demo Banner */}
      <DemoBanner />

      {/* Main Three-Column Layout Container */}
      <div className="relative z-10 flex flex-1 overflow-hidden">
        {/* Column 1: Left Navigation Sidebar */}
        <div className={`hidden lg:block shrink-0 ${isLeftCollapsed ? 'w-20' : 'w-72'}`}>
          <LeftSidebar
            currentPage={currentPage}
            onSelectPage={onSelectPage}
            isCollapsed={isLeftCollapsed}
            onToggleCollapse={() => setIsLeftCollapsed(!isLeftCollapsed)}
          />
        </div>

        {/* Mobile Left Sidebar Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 flex lg:hidden">
            <div
              className="fixed inset-0 bg-black/80 backdrop-blur-sm"
              onClick={() => setMobileMenuOpen(false)}
            />
            <div className="relative z-10 w-72 h-full bg-finwell-sidebar">
              <LeftSidebar
                currentPage={currentPage}
                onSelectPage={(page) => {
                  onSelectPage(page);
                  setMobileMenuOpen(false);
                }}
                isCollapsed={false}
                onToggleCollapse={() => setMobileMenuOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Column 2: Middle Sidebar (Conversation History / AI Hub) */}
        {showMiddleSidebar && (
          <div className="hidden md:block shrink-0">
            <MiddleSidebar
              onOpenSettings={() => onSelectPage('settings')}
              onNavigateToChat={() => onSelectPage('ai-chat')}
            />
          </div>
        )}

        {/* Column 3: Main Dynamic Content Area */}
        <main className="flex-1 flex flex-col min-w-0 overflow-y-auto min-h-screen">
          {/* Mobile Header Bar */}
          <div className="flex lg:hidden items-center justify-between p-4 border-b border-white/5 bg-finwell-card/80 backdrop-blur-md">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-2 text-finwell-muted hover:text-white rounded-lg bg-finwell-surface"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-finwell-cyan" />
              <span className="font-bold text-white text-sm">FinWell AI</span>
            </div>

            <button
              onClick={() => onSelectPage('ai-chat')}
              className="p-2 text-finwell-cyan hover:text-white rounded-lg bg-finwell-surface"
              title="Open AI Chat"
            >
              <MessageSquare className="h-5 w-5" />
            </button>
          </div>

          {/* Page View Slot */}
          <div className="flex-1">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
