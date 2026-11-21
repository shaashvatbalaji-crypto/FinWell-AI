import { apiClient } from '../api/apiClient';
import { Conversation, ChatMessage, AIResponseEvidence } from '../../types';
import {
  MOCK_CONVERSATIONS,
  MOCK_CHAT_MESSAGES,
} from '../../mock/mockData';

let inMemoryConversations = [...MOCK_CONVERSATIONS];
let inMemoryMessages: Record<string, ChatMessage[]> = { ...MOCK_CHAT_MESSAGES };

export const SUGGESTED_QUERIES = [
  'Analyse my financial health.',
  'What are my biggest expenses?',
  'Compare my monthly income.',
  'Find unusual transactions.',
  'Explain my cash flow.',
  'Identify possible duplicate transactions.',
];

export const aiChatService = {
  async getConversations(): Promise<Conversation[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      return [...inMemoryConversations];
    }

    const res = await apiClient.request<{
      success: boolean;
      conversations: Conversation[];
    }>('/ai/conversations');
    return res.conversations;
  },

  async createConversation(title?: string): Promise<Conversation> {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: title || 'New Financial Session',
      created_at: new Date().toISOString(),
      time_group: 'Today',
      message_count: 0,
    };
    inMemoryConversations.unshift(newConv);
    inMemoryMessages[newConv.id] = [];
    return newConv;
  },

  async deleteConversation(id: string): Promise<boolean> {
    inMemoryConversations = inMemoryConversations.filter((c) => c.id !== id);
    delete inMemoryMessages[id];
    return true;
  },

  async getMessages(conversationId: string): Promise<ChatMessage[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 250));
      return inMemoryMessages[conversationId] || [];
    }

    const res = await apiClient.request<{
      success: boolean;
      messages: ChatMessage[];
    }>(`/ai/conversations/${conversationId}/messages`);
    return res.messages;
  },

  async sendMessage(
    conversationId: string,
    prompt: string
  ): Promise<{ userMessage: ChatMessage; aiMessage: ChatMessage }> {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      conversation_id: conversationId,
      sender: 'user',
      text: prompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    if (!inMemoryMessages[conversationId]) {
      inMemoryMessages[conversationId] = [];
    }
    inMemoryMessages[conversationId].push(userMsg);

    if (apiClient.isMockMode()) {
      // Realistic generation delay
      await new Promise((r) => setTimeout(r, 1200));

      const aiResponse = generateIntelligentResponse(conversationId, prompt);
      inMemoryMessages[conversationId].push(aiResponse);

      // Update conversation title if first message
      const conv = inMemoryConversations.find((c) => c.id === conversationId);
      if (conv && conv.message_count === 0) {
        conv.title = prompt.length > 25 ? prompt.slice(0, 25) + '...' : prompt;
        conv.message_count = 2;
      }

      return { userMessage: userMsg, aiMessage: aiResponse };
    }

    // Live AI query orchestrator call to FastAPI backend
    const res = await apiClient.request<{
      user_message: ChatMessage;
      ai_message: ChatMessage;
    }>(`/ai/conversations/${conversationId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });

    return {
      userMessage: res.user_message,
      aiMessage: res.ai_message,
    };
  },
};

function generateIntelligentResponse(conversationId: string, prompt: string): ChatMessage {
  const p = prompt.toLowerCase();
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // 1. Comparison or income
  if (p.includes('compare') || p.includes('income')) {
    return {
      id: `msg-ai-${Date.now()}`,
      conversation_id: conversationId,
      sender: 'ai',
      text: `### Q1 Comprehensive Income Analysis\n\nHere is the audited comparison of your monthly income across current year vs prior year. Your primary revenue trajectory is experiencing sustained **+12.4% expansion** driven primarily by high-ticket consulting payouts and index dividends.\n\n* **January:** $18,400 (vs $15,200)\n* **February:** $21,500 (vs $16,800)\n* **March:** $24,800 (vs $18,100)\n\nNet cash retention remains resilient at **62.01%** after deducting recurring debt obligations and tech subscriptions.`,
      timestamp,
      inline_chart: {
        chart_type: 'dual_line',
        title: 'Monthly Income Velocity: 2026 vs 2025 (USD)',
        keys: [
          { key: 'current_year', name: 'Current Year (2026)', color: '#4263FF' },
          { key: 'last_year', name: 'Prior Year (2025)', color: '#20D9F2' },
        ],
        data: [
          { month: 'Jan', current_year: 18400, last_year: 15200 },
          { month: 'Feb', current_year: 21500, last_year: 16800 },
          { month: 'Mar', current_year: 24800, last_year: 18100 },
        ],
      },
      financial_summary: {
        total_analyzed: '$64,700 Q1 Total',
        variance: '+12.4% Annual Expansion',
        key_takeaway: 'Strongest inflow recorded from Stripe AI consulting receipts ($24,800).',
      },
      evidence: {
        reporting_period: 'Jan 1, 2026 - Mar 24, 2026',
        mysql_evidence: {
          table_queried: 'transactions JOIN accounts ON transactions.account_id = accounts.account_id',
          record_count: 48,
          query_latency_ms: 19,
          relevant_transaction_ids: [1001, 1008, 982],
          filter_applied: "direction = 'credit' AND category NOT LIKE '%Transfer%'",
        },
        chroma_evidence: [
          {
            chunk_id: 'chroma_stmt_chase_p2',
            document_name: 'Chase_Reserve_March_2026_Statement.pdf',
            page_number: 2,
            similarity_score: 0.96,
            extracted_snippet: '...Direct deposit verified: Stripe Enterprise Services - $8,500.00 posted on 03/24...',
            extracted_date: '2026-03-24',
          },
        ],
        data_limitations: 'Calculations exclude unposted and pending clearing transfers.',
        confidence: 97,
      },
    };
  }

  // 2. Biggest expenses
  if (p.includes('expense') || p.includes('spending') || p.includes('spend')) {
    return {
      id: `msg-ai-${Date.now()}`,
      conversation_id: conversationId,
      sender: 'ai',
      text: `### Expenditure Breakdown & Outflow Vectors\n\nYour total recorded outflows for March stand at **$9,420.50**. Here is how your capital was distributed across major expenditure categories:\n\n1. **Housing & Utilities:** $3,200.00 (33.9%)\n2. **Cloud Infrastructure & AI Compute:** $1,850.20 (19.6%)\n3. **Investment Allocation:** $1,500.00 (15.9%)\n4. **Dining & Lifestyle:** $1,240.50 (13.2%)\n5. **Health & Wellness:** $890.00 (9.4%)\n\n**Key Observation:** AWS & OpenAI API compute expenses grew by 14% compared to February due to accelerated model training sessions.`,
      timestamp,
      inline_chart: {
        chart_type: 'donut',
        title: 'Spending by Category (March 2026)',
        keys: [{ key: 'amount', name: 'Expenditure ($)', color: '#4263FF' }],
        data: [
          { name: 'Housing & Utilities', value: 3200, color: '#4263FF' },
          { name: 'Cloud & Tech', value: 1850, color: '#20D9F2' },
          { name: 'Investment', value: 1500, color: '#36D399' },
          { name: 'Dining', value: 1240, color: '#875BFF' },
          { name: 'Health', value: 890, color: '#FBBF24' },
          { name: 'Travel', value: 740, color: '#FB7185' },
        ],
      },
      financial_summary: {
        total_analyzed: '$9,420.50 Analyzed',
        variance: '-3.8% MoM Reduction',
        key_takeaway: 'Non-discretionary overhead remains steady within 42% of monthly cap.',
      },
      evidence: {
        reporting_period: 'March 1 - March 24, 2026',
        mysql_evidence: {
          table_queried: 'transactions WHERE direction = "debit"',
          record_count: 52,
          query_latency_ms: 14,
          relevant_transaction_ids: [1002, 1005, 1007],
          filter_applied: "direction = 'debit' AND is_reconciled = true",
        },
        chroma_evidence: [
          {
            chunk_id: 'chroma_stmt_aws_p1',
            document_name: 'Chase_Reserve_March_2026_Statement.pdf',
            page_number: 1,
            similarity_score: 0.93,
            extracted_snippet: '...AMAZON WEB SERVICES SEATTLE WA - $642.50 on 03/23/2026...',
            extracted_date: '2026-03-23',
          },
        ],
        data_limitations: 'Excludes internal inter-account transfers.',
        confidence: 99,
      },
    };
  }

  // 3. Duplicates or reconciliation
  if (p.includes('duplicate') || p.includes('unusual') || p.includes('reconcil')) {
    return {
      id: `msg-ai-${Date.now()}`,
      conversation_id: conversationId,
      sender: 'ai',
      text: `### Reconciliation Alert: Flagged Anomalies\n\nFinWell AI's reconciliation engine has identified **1 high-confidence duplicate** and **1 pending internal transfer** requiring review:\n\n* **Duplicate Charge Identified (96% Confidence):**\n  * **Merchant:** GitHub Copilot Enterprise Seats\n  * **Account:** Executive Platinum Card (•••• 8821)\n  * **Amount:** $180.00 charged twice within a 4-minute window on March 21.\n  * **Recommendation:** Submit merchant inquiry or initiate automated dispute workflow in the **Reconciliation Centre**.\n* **Cross-Account Transfer (94% Confidence):**\n  * -$5,000.00 debit from Checking 4829 matched with +$5,000.00 credit in Vanguard Savings 7914.`,
      timestamp,
      financial_summary: {
        total_analyzed: '2 Flagged Transactions',
        variance: '$180.00 Potential Recovery',
        key_takeaway: 'Potential duplicate subscription charge detected and isolated.',
      },
      evidence: {
        reporting_period: 'March 15 - March 24, 2026',
        mysql_evidence: {
          table_queried: 'reconciliation_cases JOIN transactions ON reconciliation_cases.source_transaction_id = transactions.transaction_id',
          record_count: 2,
          query_latency_ms: 22,
          relevant_transaction_ids: [1005, 1006],
          filter_applied: "status = 'needs_review' OR status = 'suggested'",
        },
        chroma_evidence: [
          {
            chunk_id: 'chroma_stmt_github_dup',
            document_name: 'Chase_Reserve_March_2026_Statement.pdf',
            page_number: 2,
            similarity_score: 0.97,
            extracted_snippet: '...03/21 GITHUB COPILOT $180.00 | 03/21 GITHUB COPILOT $180.00...',
            extracted_date: '2026-03-21',
          },
        ],
        data_limitations: 'Subject to final clearing by card issuer.',
        confidence: 96,
      },
    };
  }

  // Default fallback financial overview
  return {
    id: `msg-ai-${Date.now()}`,
    conversation_id: conversationId,
    sender: 'ai',
    text: `### FinWell AI Financial Synthesis\n\nI have evaluated your active portfolio, transaction ledgers, and indexed statement documents across all connected banking nodes.\n\n* **Liquid Position:** **$122,330.65** across 4 monitored institutions.\n* **Net Cash Velocity:** **+$15,379.50** for the current billing cycle.\n* **Savings Efficiency:** Currently executing at **62.01%**, exceeding standard personal finance benchmarks by 22%.\n\nWould you like me to generate a detailed breakdown of your tax deductions, analyze liquidity ratios, or audit your recent recurring subscriptions?`,
    timestamp,
    financial_summary: {
      total_analyzed: '$122,330.65 Monitored',
      variance: '+8.7% Portfolio Gain',
      key_takeaway: 'Financial health score is Grade A+ (Optimal Liquidity & Surplus Flow).',
    },
    evidence: {
      reporting_period: 'Current Year-to-Date 2026',
      mysql_evidence: {
        table_queried: 'accounts JOIN transactions ON accounts.account_id = transactions.account_id',
        record_count: 140,
        query_latency_ms: 16,
        relevant_transaction_ids: [1001, 1002, 1003, 1004],
        filter_applied: 'user_id = 101',
      },
      chroma_evidence: [
        {
          chunk_id: 'chroma_stmt_apex_balance',
          document_name: 'Apex_Federal_Checking_Q1_2026.pdf',
          page_number: 1,
          similarity_score: 0.92,
          extracted_snippet: '...Verified closing statement reconciliation balance: $38,450.25...',
          extracted_date: '2026-03-20',
        },
      ],
      data_limitations: 'Includes posted transactions across all synchronized accounts.',
      confidence: 98,
    },
  };
}
