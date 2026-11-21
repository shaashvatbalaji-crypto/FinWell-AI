import React, { createContext, useContext, useState, useEffect } from 'react';
import { Conversation, ChatMessage, AIResponseEvidence } from '../types';
import { aiChatService } from '../services/ai/aiChatService';

interface ChatContextType {
  conversations: Conversation[];
  activeConversationId: string;
  messages: ChatMessage[];
  isGenerating: boolean;
  activeEvidence: AIResponseEvidence | null;
  searchFilter: string;
  setSearchFilter: (query: string) => void;
  setActiveConversationId: (id: string) => void;
  setActiveEvidence: (evidence: AIResponseEvidence | null) => void;
  createNewChat: () => Promise<string>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>('conv-1');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [activeEvidence, setActiveEvidence] = useState<AIResponseEvidence | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

  useEffect(() => {
    // Load initial conversations
    aiChatService.getConversations().then((data) => {
      setConversations(data);
      if (data.length > 0 && !activeConversationId) {
        setActiveConversationId(data[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (activeConversationId) {
      aiChatService.getMessages(activeConversationId).then((msgs) => {
        setMessages(msgs);
        // If the last message has evidence, set it or clear
        const lastAiMsg = [...msgs].reverse().find((m) => m.sender === 'ai' && m.evidence);
        if (lastAiMsg?.evidence) {
          setActiveEvidence(lastAiMsg.evidence);
        } else {
          setActiveEvidence(null);
        }
      });
    }
  }, [activeConversationId]);

  const createNewChat = async (): Promise<string> => {
    const newConv = await aiChatService.createConversation('New Financial Session');
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    setMessages([]);
    setActiveEvidence(null);
    return newConv.id;
  };

  const deleteConversation = async (id: string) => {
    await aiChatService.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      const remaining = conversations.filter((c) => c.id !== id);
      if (remaining.length > 0) {
        setActiveConversationId(remaining[0].id);
      } else {
        await createNewChat();
      }
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || !activeConversationId) return;

    // Optimistically add user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsGenerating(true);

    try {
      const res = await aiChatService.sendMessage(activeConversationId, text);
      // Replace or update state
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...withoutTemp, res.userMessage, res.aiMessage];
      });

      if (res.aiMessage.evidence) {
        setActiveEvidence(res.aiMessage.evidence);
      }

      // Refresh conversations list to update title / counts
      const updatedConvs = await aiChatService.getConversations();
      setConversations(updatedConvs);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeConversationId,
        messages,
        isGenerating,
        activeEvidence,
        searchFilter,
        setSearchFilter,
        setActiveConversationId,
        setActiveEvidence,
        createNewChat,
        deleteConversation,
        sendMessage,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
