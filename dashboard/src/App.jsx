import { useState } from 'react'
import KeySetup from './components/KeySetup.jsx'
import Overview from './components/Overview.jsx'
import Playground from './components/Playground.jsx'
import ApiKeys from './components/ApiKeys.jsx'

const TABS = ['Overview', 'Playground', 'API Keys']

export default function App() {
  const [apiKey, setApiKey]     = useState(() => localStorage.getItem('bvt_api_key') || '')
  const [activeTab, setActiveTab] = useState('Overview')

  const saveKey = (key) => { localStorage.setItem('bvt_api_key', key); setApiKey(key) }
  const clearKey = () => { localStorage.removeItem('bvt_api_key'); setApiKey('') }

  if (!apiKey) return <KeySetup onSave={saveKey} />

  return (
    <div className="min-h-screen bg-brand-bg flex flex-col">
      {/* ── Floating pill nav ── */}
      <div className="sticky top-0 z-50 px-6 pt-5 pb-3">
        <header className="bg-white rounded-2xl border border-brand-border shadow-sm px-6 py-3.5 flex items-center justify-between max-w-7xl mx-auto">
          {/* Logo */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="font-serif text-[1.35rem] font-medium text-brand-navy leading-none">Brevitas</span>
            <span className="font-mono text-[9px] tracking-widest uppercase text-brand-muted leading-none pt-0.5">
              Systems
            </span>
          </div>

          {/* Tabs */}
          <nav className="flex items-center gap-1">
            {TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-xl text-[11px] tracking-widest uppercase font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-brand-blue-dim text-brand-blue'
                    : 'text-brand-muted hover:text-brand-navy'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>

          {/* Right action */}
          <button
            onClick={clearKey}
            className="text-[11px] text-brand-muted hover:text-brand-navy transition-colors tracking-wide shrink-0"
          >
            Change key
          </button>
        </header>
      </div>

      {/* ── Page content ── */}
      <main className="flex-1 px-6 pt-6 pb-16 max-w-7xl mx-auto w-full">
        {activeTab === 'Overview'   && <Overview   apiKey={apiKey} />}
        {activeTab === 'Playground' && <Playground apiKey={apiKey} />}
        {activeTab === 'API Keys'   && <ApiKeys    apiKey={apiKey} />}
      </main>
    </div>
  )
}
