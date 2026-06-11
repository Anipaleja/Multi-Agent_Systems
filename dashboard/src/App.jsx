import { useState } from 'react'
import KeySetup from './components/KeySetup.jsx'
import Overview from './components/Overview.jsx'
import Playground from './components/Playground.jsx'
import ApiKeys from './components/ApiKeys.jsx'

const TABS = ['Overview', 'Playground', 'API Keys']

export default function App() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('bvt_api_key') || '')
  const [activeTab, setActiveTab] = useState('Overview')

  const saveKey = (key) => {
    localStorage.setItem('bvt_api_key', key)
    setApiKey(key)
  }

  const clearKey = () => {
    localStorage.removeItem('bvt_api_key')
    setApiKey('')
  }

  if (!apiKey) return <KeySetup onSave={saveKey} />

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-violet-400">⚡</span>
          <span className="font-semibold text-lg tracking-tight">Brevitas</span>
          <span className="hidden sm:block text-slate-500 text-sm">Token Efficiency API</span>
        </div>
        <button
          onClick={clearKey}
          className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
        >
          Change key
        </button>
      </header>

      <nav className="border-b border-slate-800 px-6 shrink-0">
        <div className="flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-violet-500 text-violet-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </nav>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'Overview'   && <Overview   apiKey={apiKey} />}
        {activeTab === 'Playground' && <Playground apiKey={apiKey} />}
        {activeTab === 'API Keys'   && <ApiKeys    apiKey={apiKey} />}
      </main>
    </div>
  )
}
