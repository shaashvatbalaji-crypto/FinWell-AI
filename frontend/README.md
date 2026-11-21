# FinWell AI — Premium 3D Fintech Frontend

An intelligent, commercial-grade personal finance management and autonomous reconciliation platform built with **React 19**, **Vite**, **TypeScript**, **Tailwind CSS**, and **Three.js**.

Inspired by the dark navy, electric-blue, and violet aesthetic of the NeuroBank AI visual design language.

---

## 🚀 Live Preview & Development

The Vite development server is running locally:
```bash
# In the frontend directory:
npm run dev
```
Open **[http://localhost:5173/](http://localhost:5173/)** in your browser.

---

## 🎨 Visual Design System

- **Background Base**: `#080914` (Deep obsidian navy)
- **Sidebar Background**: `#0D0E1B`
- **Card Glass Surface**: `#121426` & `#191C30` with `backdrop-filter: blur(16px)`
- **Electric Blue (Primary)**: `#4263FF`
- **Cyan Accent**: `#20D9F2`
- **Violet Accent**: `#875BFF`
- **Typography**: Plus Jakarta Sans, Inter, JetBrains Mono
- **3D Engine**: Three.js WebGL canvas with interactive orbital rings, core glow, particle dust, and mouse-reactive tilt.

---

## 🧱 Component & Service Architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── 3d/
│   │   │   ├── FinancialOrb3D.tsx        # Three.js glowing financial orb
│   │   │   ├── BackgroundParticles3D.tsx # Subtle floating ambient particles
│   │   │   └── TiltCard.tsx              # Interactive 3D hover perspective tilt
│   │   ├── common/
│   │   │   ├── Badge.tsx                 # Glowing fintech status pills
│   │   │   ├── Button.tsx                # Polished action buttons with loaders
│   │   │   ├── DemoBanner.tsx            # Discreet mock mode indicator
│   │   │   ├── Modal.tsx                 # Accessible dialog modal
│   │   │   └── StatCard.tsx              # Top metric card with trend indicators
│   │   └── layout/
│   │       ├── AppLayout.tsx             # 3-column desktop layout coordinator
│   │       ├── LeftSidebar.tsx           # Profile, active navigation, theme switch
│   │       └── MiddleSidebar.tsx         # AI chat history (Today, Yesterday, 7 Days)
│   ├── pages/
│   │   ├── Dashboard/                    # 4 summary KPIs, cash flow trends, category donut
│   │   ├── AIChat/                       # Centrepiece AI chat, dual-line charts, evidence drawer
│   │   ├── Accounts/                     # Vault cards, add account modal, ledger history
│   │   ├── Transactions/                 # Advanced filtered & sorted table with pagination
│   │   ├── Analytics/                    # Macro cash dynamics, multi-period range filters
│   │   ├── Reconciliation/               # Side-by-side transaction audit & duplicate matcher
│   │   ├── Documents/                    # PDF drag-and-drop & animated 7-step pipeline
│   │   ├── Reports/                      # Executive summaries, PDF/CSV export previews
│   │   ├── Settings/                     # Profile, theme, currency, FastAPI connection panel
│   │   ├── Login/                        # 3D orb visual login with 1-click demo fill
│   │   ├── Register/                     # Account creation with password strength meter
│   │   └── ForgotPassword/               # Credential recovery workflow
│   ├── services/
│   │   ├── api/apiClient.ts              # Centralized fetch wrapper & mock switch
│   │   ├── auth/authService.ts           # POST /api/auth/login, /register
│   │   ├── accounts/accountService.ts    # GET & POST /api/accounts
│   │   ├── transactions/transactionService.ts # GET /api/transactions
│   │   ├── analytics/analyticsService.ts # /api/analytics/summary & monthly
│   │   ├── documents/documentService.ts  # Ingestion pipeline & PDF upload
│   │   ├── reconciliation/reconciliationService.ts # Heuristic match cases
│   │   └── ai/aiChatService.ts           # RAG responses with MySQL & ChromaDB evidence
│   ├── context/
│   │   ├── AuthContext.tsx
│   │   ├── ThemeContext.tsx
│   │   └── ChatContext.tsx
│   ├── mock/
│   │   └── mockData.ts                   # Realistic, clearly-labelled demo data
│   ├── types/
│   │   └── index.ts                      # Strict TypeScript interfaces matching FastAPI schemas
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── tailwind.config.js
└── package.json
```

---

## 🔌 Connecting to Existing FastAPI Backend

The frontend is specifically prepared for your existing FastAPI backend:

1. In **Settings** (`/settings`), toggle **"Operation Mode"** from *Mock Data Simulation* to *Live API Direct*.
2. Ensure your FastAPI server is running on `http://localhost:8000`.
3. Test connectivity using the built-in **"Ping Health"** button in Settings.
4. All service modules (`authService`, `accountService`, `transactionService`, `analyticsService`, `documentService`) automatically switch from in-memory mock responses to real HTTP requests against your endpoints.
