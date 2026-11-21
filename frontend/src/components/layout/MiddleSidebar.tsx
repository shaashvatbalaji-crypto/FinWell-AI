import React, { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  Settings as SettingsIcon,
  X,
} from 'lucide-react';
import { useChat } from '../../context/ChatContext';

interface MiddleSidebarProps {
  onOpenSettings: () => void;
  className?: string;
  onNavigateToChat?: () => void;
}

export const MiddleSidebar: React.FC<MiddleSidebarProps> = ({
  onOpenSettings,
  className = '',
  onNavigateToChat,
}) => {
  const {
    conversations,
    activeConversationId,
    setActiveConversationId,
    createNewChat,
    deleteConversation,
    searchFilter,
    setSearchFilter,
  } = useChat();

  const [isSearching, setIsSearching] = useState<boolean>(false);

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const todayList = filteredConversations.filter((c) => c.time_group === 'Today');
  const yesterdayList = filteredConversations.filter((c) => c.time_group === 'Yesterday');
  const last7DaysList = filteredConversations.filter((c) => c.time_group === 'Last 7 days');

  const handleSelect = (id: string) => {
    setActiveConversationId(id);
    if (onNavigateToChat) {
      onNavigateToChat();
    }
  };

  const handleCreateNew = async () => {
    await createNewChat();
    if (onNavigateToChat) {
      onNavigateToChat();
    }
  };

  const renderSection = (title: string, items: typeof conversations) => {
    if (items.length === 0) return null;

    return (
      <div className="mb-5">
        <h5 className="px-3 mb-2 text-[11px] font-semibold tracking-wider text-finwell-dim uppercase">
          {title}
        </h5>
        <div className="flex flex-col gap-1">
          {items.map((item) => {
            const isActive = activeConversationId === item.id;
            return (
              <div
                key={item.id}
                onClick={() => handleSelect(item.id)}
                className={`group relative flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium cursor-pointer transition-all duration-200 ${
                  isActive
                    ? 'border border-finwell-primary/40 bg-finwell-primary/15 text-white shadow-sm'
                    : 'text-finwell-muted hover:bg-white/[0.04] hover:text-white border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <MessageSquare
                    className={`h-4 w-4 shrink-0 ${
                      isActive ? 'text-finwell-cyan' : 'text-finwell-dim group-hover:text-finwell-muted'
                    }`}
                  />
                  <span className="truncate">{item.title}</span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {/* Delete Button (visible on hover) */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteConversation(item.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-finwell-dim hover:text-finwell-danger transition-opacity rounded"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>

                  {/* Active Blue Dot (from reference image) */}
                  {isActive && (
                    <span className="h-2 w-2 rounded-full bg-finwell-primary shadow-[0_0_8px_#4263FF]" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div
      className={`relative z-10 flex flex-col justify-between border-r border-white/5 bg-finwell-card/60 backdrop-blur-md w-72 min-h-screen p-4 select-none ${className}`}
    >
      {/* Top Header & New Chat button */}
      <div className="flex flex-col">
        <div className="flex items-center justify-between mb-4 px-1">
          <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
            FinWell <span className="text-finwell-cyan">AI</span>
          </h3>
          <span className="text-[10px] bg-finwell-surface border border-white/5 text-finwell-muted px-2 py-0.5 rounded-full">
            History
          </span>
        </div>

        {/* Action Controls: + New chat & Search */}
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={handleCreateNew}
            className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-finwell-primary hover:bg-finwell-primary-hover px-4 py-2.5 text-xs font-semibold text-white transition-all duration-200 shadow-glow-sm active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            <span>New chat</span>
          </button>

          <button
            onClick={() => setIsSearching(!isSearching)}
            className={`flex h-10 w-10 items-center justify-center rounded-xl border transition-colors ${
              isSearching
                ? 'border-finwell-cyan bg-finwell-cyan/10 text-finwell-cyan'
                : 'border-white/10 bg-finwell-surface text-finwell-muted hover:border-white/20 hover:text-white'
            }`}
            title="Search conversations"
          >
            <Search className="h-4 w-4" />
          </button>
        </div>

        {/* Expandable Search Input */}
        {isSearching && (
          <div className="relative mb-4">
            <input
              type="text"
              placeholder="Search chats..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3 py-2 text-xs text-white placeholder-finwell-dim focus:border-finwell-cyan focus:outline-none"
              autoFocus
            />
            {searchFilter && (
              <button
                onClick={() => setSearchFilter('')}
                className="absolute right-2.5 top-2.5 text-finwell-dim hover:text-white"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Grouped Conversation History */}
        <div className="overflow-y-auto max-h-[calc(100vh-250px)] pr-1">
          {renderSection('Today', todayList)}
          {renderSection('Yesterday', yesterdayList)}
          {renderSection('Last 7 days', last7DaysList)}

          {filteredConversations.length === 0 && (
            <div className="p-6 text-center text-xs text-finwell-dim">
              No conversations found.
            </div>
          )}
        </div>
      </div>

      {/* Bottom Settings Shortcut Button (Faithful to NeuroBank reference image) */}
      <div className="pt-3 border-t border-white/5">
        <button
          onClick={onOpenSettings}
          className="flex w-full items-center gap-2.5 rounded-xl border border-white/5 bg-finwell-surface/80 hover:bg-finwell-surface px-3.5 py-2.5 text-xs font-semibold text-finwell-text hover:text-white transition-colors"
        >
          <SettingsIcon className="h-4 w-4 text-finwell-muted" />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
};
