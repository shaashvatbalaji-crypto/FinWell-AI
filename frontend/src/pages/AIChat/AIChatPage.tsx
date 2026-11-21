import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Paperclip,
  Copy,
  Check,
  RotateCcw,
  Sparkles,
  Database,
  Search,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { useChat } from '../../context/ChatContext';
import { SUGGESTED_QUERIES } from '../../services/ai/aiChatService';
import { ChatMessage, AIResponseEvidence } from '../../types';
import { Badge } from '../../components/common/Badge';

export const AIChatPage: React.FC = () => {
  const {
    messages,
    sendMessage,
    isGenerating,
    activeEvidence,
    setActiveEvidence,
  } = useChat();

  const [inputPrompt, setInputPrompt] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showEvidencePanel, setShowEvidencePanel] = useState<boolean>(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSend = async () => {
    if (!inputPrompt.trim() || isGenerating) return;
    const text = inputPrompt;
    setInputPrompt('');
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRegenerate = async (msg: ChatMessage) => {
    // Find the previous user prompt
    const idx = messages.findIndex((m) => m.id === msg.id);
    if (idx > 0 && messages[idx - 1].sender === 'user') {
      await sendMessage(messages[idx - 1].text);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-65px)] overflow-hidden bg-finwell-bg">
      {/* Top Ambient Chart Header / Status Banner (from NeuroBank reference) */}
      <div className="relative border-b border-white/5 bg-finwell-card/30 px-6 py-3 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-finwell-primary/20 text-finwell-cyan shadow-glow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              FinWell Autonomous AI Assistant
              <Badge variant="cyan" size="sm">
                Qwen 2.5:3B Ready
              </Badge>
            </h2>
            <p className="text-[11px] text-finwell-dim">
              Dual-source validation: MySQL Transaction Ledger + ChromaDB Vector Chunks
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowEvidencePanel(!showEvidencePanel)}
          className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
            showEvidencePanel
              ? 'border-finwell-primary/40 bg-finwell-primary/10 text-finwell-cyan'
              : 'border-white/10 bg-finwell-surface text-finwell-muted hover:text-white'
          }`}
        >
          <Database className="h-3.5 w-3.5" />
          <span>Evidence Panel</span>
          {showEvidencePanel ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Main Chat Workspace */}
      <div className="flex flex-1 overflow-hidden">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto py-12">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-finwell-primary via-finwell-cyan to-finwell-violet p-0.5 shadow-glow-md mb-4">
                <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-finwell-card">
                  <Sparkles className="h-8 w-8 text-finwell-cyan" />
                </div>
              </div>
              <h3 className="text-lg font-bold text-white mb-2">
                What financial insights can FinWell discover for you today?
              </h3>
              <p className="text-xs text-finwell-muted mb-6 leading-relaxed">
                Ask about income growth, largest expenditures, duplicate charges, or cross-account reconciliation.
              </p>

              {/* Suggested Questions Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full text-left">
                {SUGGESTED_QUERIES.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(q)}
                    className="rounded-xl border border-white/5 bg-finwell-card hover:bg-finwell-surface hover:border-finwell-primary/30 p-3 text-xs text-finwell-text hover:text-white transition-all duration-200 text-left"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex flex-col ${
                  message.sender === 'user' ? 'items-end' : 'items-start'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center gap-2 mb-1.5 px-1">
                  {message.sender === 'ai' && (
                    <div className="flex items-center gap-1.5">
                      <div className="flex h-5 w-5 items-center justify-center rounded-md bg-finwell-primary text-white shadow-glow-sm">
                        <Sparkles className="h-3 w-3 text-finwell-cyan" />
                      </div>
                      <span className="text-xs font-bold text-white">FinWell AI</span>
                    </div>
                  )}
                  <span className="text-[10px] text-finwell-dim">{message.timestamp}</span>
                </div>

                {/* Message Bubble */}
                <div
                  className={`relative max-w-3xl rounded-2xl p-5 ${
                    message.sender === 'user'
                      ? 'bg-finwell-primary/20 border border-finwell-primary/40 text-white rounded-br-sm'
                      : 'bg-finwell-card/90 border border-white/10 text-finwell-text rounded-bl-sm shadow-card-glass backdrop-blur-md'
                  }`}
                >
                  {/* Text Content */}
                  <div className="text-sm leading-relaxed whitespace-pre-line font-normal space-y-2">
                    {message.text}
                  </div>

                  {/* Inline Chart (Faithful to NeuroBank reference image) */}
                  {message.inline_chart && (
                    <div className="mt-5 pt-4 border-t border-white/5">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                          <TrendingUp className="h-3.5 w-3.5 text-finwell-cyan" />
                          {message.inline_chart.title}
                        </h4>
                        <div className="flex items-center gap-3">
                          {message.inline_chart.keys.map((k) => (
                            <span key={k.key} className="flex items-center gap-1.5 text-[11px] text-finwell-muted">
                              <span
                                className="h-2 w-2 rounded-full"
                                style={{ backgroundColor: k.color }}
                              />
                              {k.name}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="h-56 w-full rounded-xl bg-finwell-surface/60 p-3 border border-white/5">
                        {message.inline_chart.chart_type === 'dual_line' ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={message.inline_chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                              <XAxis dataKey="month" stroke="#656B8A" fontSize={11} tickLine={false} />
                              <YAxis stroke="#656B8A" fontSize={11} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: '#121426',
                                  borderColor: 'rgba(66,99,255,0.3)',
                                  borderRadius: '8px',
                                  color: '#F5F6FF',
                                  fontSize: '12px',
                                }}
                              />
                              <Line
                                type="monotone"
                                dataKey="current_year"
                                name="Current Year"
                                stroke="#4263FF"
                                strokeWidth={3}
                                dot={{ fill: '#4263FF', r: 4 }}
                                activeDot={{ r: 6, fill: '#20D9F2' }}
                              />
                              <Line
                                type="monotone"
                                dataKey="last_year"
                                name="Last Year"
                                stroke="#20D9F2"
                                strokeWidth={2.5}
                                strokeDasharray="4 4"
                                dot={{ fill: '#20D9F2', r: 3 }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={message.inline_chart.data}
                                cx="50%"
                                cy="50%"
                                innerRadius={45}
                                outerRadius={70}
                                paddingAngle={5}
                                dataKey="value"
                              >
                                {message.inline_chart.data.map((entry: any, index: number) => (
                                  <Cell key={`cell-${index}`} fill={entry.color || '#4263FF'} />
                                ))}
                              </Pie>
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: '#121426',
                                  borderColor: 'rgba(66,99,255,0.3)',
                                  borderRadius: '8px',
                                  color: '#F5F6FF',
                                  fontSize: '12px',
                                }}
                                formatter={(val: any) => [`$${val}`, 'Amount']}
                              />
                              <Legend
                                wrapperStyle={{ fontSize: '11px', color: '#9298B3' }}
                                iconSize={8}
                              />
                            </PieChart>
                          </ResponsiveContainer>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Financial Summary Pill Bar */}
                  {message.financial_summary && (
                    <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2.5 rounded-xl bg-finwell-surface/70 border border-white/5 p-3 text-xs">
                      <div>
                        <span className="text-finwell-dim text-[10px] uppercase font-semibold">Analyzed Volume</span>
                        <p className="font-bold text-white mt-0.5">{message.financial_summary.total_analyzed}</p>
                      </div>
                      <div>
                        <span className="text-finwell-dim text-[10px] uppercase font-semibold">Variance Delta</span>
                        <p className="font-bold text-finwell-success mt-0.5">{message.financial_summary.variance}</p>
                      </div>
                      <div className="sm:col-span-1">
                        <span className="text-finwell-dim text-[10px] uppercase font-semibold">Core Synthesis</span>
                        <p className="text-[11px] text-finwell-muted mt-0.5 truncate">{message.financial_summary.key_takeaway}</p>
                      </div>
                    </div>
                  )}

                  {/* AI Response Footer Actions */}
                  {message.sender === 'ai' && (
                    <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-finwell-dim">
                      <div className="flex items-center gap-2">
                        {message.evidence && (
                          <button
                            onClick={() => {
                              setActiveEvidence(message.evidence!);
                              setShowEvidencePanel(true);
                            }}
                            className="inline-flex items-center gap-1 text-[11px] text-finwell-cyan hover:underline"
                          >
                            <Info className="h-3 w-3" />
                            View Verification Sources ({message.evidence.confidence}% confidence)
                          </button>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleCopy(message.id, message.text)}
                          className="flex items-center gap-1 hover:text-white transition-colors"
                          title="Copy response"
                        >
                          {copiedId === message.id ? (
                            <>
                              <Check className="h-3.5 w-3.5 text-finwell-success" />
                              <span className="text-finwell-success">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3.5 w-3.5" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>

                        <button
                          onClick={() => handleRegenerate(message)}
                          className="flex items-center gap-1 hover:text-white transition-colors"
                          title="Regenerate response"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          <span>Regenerate</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* Typing Indicator */}
          {isGenerating && (
            <div className="flex items-start gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-finwell-primary text-white">
                <Sparkles className="h-3.5 w-3.5 text-finwell-cyan animate-pulse" />
              </div>
              <div className="rounded-2xl bg-finwell-card border border-white/10 px-4 py-3 shadow-sm">
                <div className="flex items-center gap-1.5">
                  <div className="h-2 w-2 rounded-full bg-finwell-cyan animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="h-2 w-2 rounded-full bg-finwell-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="h-2 w-2 rounded-full bg-finwell-violet animate-bounce" style={{ animationDelay: '300ms' }} />
                  <span className="text-xs text-finwell-muted ml-2">FinWell AI synthesizing ledger evidence...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* AI Evidence Panel ("How FinWell answered") */}
        {showEvidencePanel && activeEvidence && (
          <aside className="w-80 border-l border-white/5 bg-finwell-card/70 backdrop-blur-md p-4 overflow-y-auto hidden xl:flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Database className="h-4 w-4 text-finwell-cyan" />
                How FinWell Answered
              </h4>
              <Badge variant="success" size="sm">
                {activeEvidence.confidence}% Confidence
              </Badge>
            </div>

            {/* Reporting Period */}
            <div className="rounded-xl bg-finwell-surface p-3 border border-white/5">
              <span className="text-[10px] text-finwell-dim uppercase font-semibold">Reporting Horizon</span>
              <p className="text-xs font-semibold text-white mt-0.5">{activeEvidence.reporting_period}</p>
            </div>

            {/* MySQL Evidence */}
            <div className="rounded-xl bg-finwell-surface p-3 border border-white/5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-finwell-primary uppercase font-bold flex items-center gap-1">
                  <Database className="h-3 w-3" /> MySQL Structured Record
                </span>
                <span className="text-[10px] text-finwell-dim">{activeEvidence.mysql_evidence.query_latency_ms}ms</span>
              </div>
              <div className="text-[11px] font-mono text-finwell-muted bg-finwell-bg/60 p-2 rounded border border-white/5 break-all">
                {activeEvidence.mysql_evidence.table_queried}
              </div>
              <div className="flex justify-between text-[11px] text-finwell-dim">
                <span>Verified Rows: {activeEvidence.mysql_evidence.record_count}</span>
                <span>Txn IDs: #{activeEvidence.mysql_evidence.relevant_transaction_ids.join(', #')}</span>
              </div>
            </div>

            {/* ChromaDB Vector Evidence */}
            <div className="space-y-2">
              <span className="text-[10px] text-finwell-cyan uppercase font-bold flex items-center gap-1">
                <Search className="h-3 w-3" /> ChromaDB Semantic Chunks
              </span>

              {activeEvidence.chroma_evidence.map((chunk) => (
                <div key={chunk.chunk_id} className="rounded-xl bg-finwell-surface p-3 border border-white/5 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-white truncate max-w-[170px]" title={chunk.document_name}>
                      {chunk.document_name}
                    </span>
                    <span className="text-finwell-cyan font-mono text-[10px]">
                      {(chunk.similarity_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="text-[11px] text-finwell-muted italic bg-finwell-bg/40 p-2 rounded border border-white/5 leading-relaxed">
                    "{chunk.extracted_snippet}"
                  </p>
                  <div className="flex justify-between text-[10px] text-finwell-dim">
                    <span>Page {chunk.page_number}</span>
                    <span>Extracted {chunk.extracted_date}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Data Limitations */}
            <div className="rounded-xl bg-finwell-warning/10 border border-finwell-warning/20 p-3 text-xs text-finwell-warning/90 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-[11px]">
                <AlertTriangle className="h-3.5 w-3.5" />
                Data Limitations Notice
              </div>
              <p className="text-[11px] text-finwell-warning/80 leading-relaxed">
                {activeEvidence.data_limitations}
              </p>
            </div>
          </aside>
        )}
      </div>

      {/* Input Area (Faithful to NeuroBank reference: glowing outline, paperclip, send button) */}
      <div className="border-t border-white/5 bg-finwell-card/40 p-4 backdrop-blur-md">
        <div className="max-w-4xl mx-auto">
          <div className="relative flex items-center rounded-2xl border border-finwell-primary/40 bg-finwell-surface/90 shadow-glow-sm focus-within:border-finwell-cyan focus-within:shadow-glow-cyan transition-all duration-300">
            {/* Attachment Button */}
            <button
              onClick={() => alert('Document attachment will be connected to ChromaDB pipeline.')}
              className="pl-4 pr-2 text-finwell-dim hover:text-white transition-colors"
              title="Attach statement or invoice"
            >
              <Paperclip className="h-4 w-4" />
            </button>

            {/* Textarea */}
            <textarea
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Can you show me a breakdown of my income sources for this year? A table or chart would be great."
              className="flex-1 bg-transparent py-3.5 px-2 text-xs md:text-sm text-white placeholder-finwell-dim focus:outline-none resize-none max-h-32"
            />

            {/* Send Button */}
            <div className="pr-3">
              <button
                onClick={handleSend}
                disabled={!inputPrompt.trim() || isGenerating}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-finwell-primary hover:bg-finwell-primary-hover text-white transition-all shadow-glow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                title="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between text-[11px] text-finwell-dim px-2">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <span className="flex items-center gap-1 text-finwell-muted">
              Powered by FinWell RAG Orchestrator
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
