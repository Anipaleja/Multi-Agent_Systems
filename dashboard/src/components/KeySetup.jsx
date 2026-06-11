import { useState } from 'react'

export default function KeySetup({ onSave }) {
  const [name, setName] = useState('')
  const [pastedKey, setPastedKey] = useState('')
  const [newKey, setNewKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  const createKey = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/v1/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() || 'default' }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setNewKey(data.api_key)
      onSave(data.api_key)
    } catch (e) {
      setError('Could not reach the API server. Make sure it is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  const copy = () => {
    navigator.clipboard.writeText(newKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="text-5xl mb-3">⚡</div>
          <h1 className="text-3xl font-bold mb-2">Brevitas</h1>
          <p className="text-slate-400 text-sm leading-relaxed">
            Token Efficiency API — reduce inter-agent tokens by ~60%,<br />retain 99% of context
          </p>
        </div>

        <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6 space-y-5">
          <div>
            <h2 className="font-semibold mb-3">Create a new API key</h2>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Project name (optional)"
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && createKey()}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
              />
              <button
                onClick={createKey}
                disabled={loading}
                className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors"
              >
                {loading ? 'Creating…' : 'Create API Key'}
              </button>
            </div>

            {newKey && (
              <div className="mt-3 bg-emerald-950 border border-emerald-800 rounded-lg p-3">
                <p className="text-xs text-emerald-400 mb-2">Key created — copy it now.</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs font-mono text-emerald-300 break-all">{newKey}</code>
                  <button
                    onClick={copy}
                    className="shrink-0 bg-emerald-800 hover:bg-emerald-700 rounded px-3 py-1.5 text-xs transition-colors"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-slate-900 px-2 text-xs text-slate-500">or use an existing key</span>
            </div>
          </div>

          <div className="space-y-2">
            <input
              type="text"
              placeholder="bvt_…"
              value={pastedKey}
              onChange={e => setPastedKey(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500 font-mono transition-colors"
            />
            <button
              onClick={() => pastedKey.trim() && onSave(pastedKey.trim())}
              disabled={!pastedKey.trim()}
              className="w-full bg-slate-700 hover:bg-slate-600 disabled:opacity-40 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors"
            >
              Use this key
            </button>
          </div>

          {error && <p className="text-red-400 text-xs">{error}</p>}
        </div>

        <p className="text-center text-slate-600 text-xs">
          Make sure the API server is running: <code className="text-slate-500">uvicorn api.server:app --reload</code>
        </p>
      </div>
    </div>
  )
}
