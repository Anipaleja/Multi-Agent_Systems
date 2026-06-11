import { useState } from 'react'

export default function KeySetup({ onSave }) {
  const [name, setName]         = useState('')
  const [pastedKey, setPastedKey] = useState('')
  const [newKey, setNewKey]     = useState('')
  const [loading, setLoading]   = useState(false)
  const [copied, setCopied]     = useState(false)
  const [error, setError]       = useState('')

  const createKey = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/v1/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() || 'default' }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setNewKey(data.api_key)
      onSave(data.api_key)
    } catch {
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
    <div className="min-h-screen bg-brand-bg flex flex-col items-center justify-center p-6">
      {/* Editorial header */}
      <div className="text-center mb-14">
        <div className="flex items-baseline justify-center gap-2 mb-6">
          <span className="font-serif text-5xl font-medium text-brand-navy">Brevitas</span>
          <span className="font-mono text-[10px] tracking-widest uppercase text-brand-muted">Systems</span>
        </div>
        <p className="font-serif text-2xl text-brand-navy-mid leading-snug">
          the layer <em className="text-brand-blue not-italic font-serif italic">between</em> your agents.
        </p>
        <p className="annotation mt-3">
          // reduce inter-agent tokens by ~60% · retain 99% of context
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-sm bg-white rounded-2xl border border-brand-border p-8 space-y-6">
        {/* Create section */}
        <div className="space-y-3">
          <p className="annotation">// create a new key</p>
          <input
            type="text"
            placeholder="Project name"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createKey()}
            className="w-full bg-brand-bg border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-navy placeholder-brand-muted focus:outline-none focus:border-brand-blue transition-colors"
          />
          <button
            onClick={createKey}
            disabled={loading}
            className="w-full bg-brand-blue hover:bg-brand-navy text-white rounded-xl px-4 py-3 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Creating…' : 'Create API key →'}
          </button>

          {newKey && (
            <div className="bg-brand-teal-dim border border-brand-teal/30 rounded-xl p-4">
              <p className="annotation text-brand-teal mb-2">// copy it now — shown once</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs font-mono text-brand-teal break-all">{newKey}</code>
                <button
                  onClick={copy}
                  className="shrink-0 border border-brand-teal/40 text-brand-teal rounded-lg px-3 py-1.5 text-xs transition-colors hover:bg-brand-teal hover:text-white"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-brand-border" />
          <span className="annotation">or</span>
          <div className="flex-1 h-px bg-brand-border" />
        </div>

        {/* Paste section */}
        <div className="space-y-3">
          <p className="annotation">// paste an existing key</p>
          <input
            type="text"
            placeholder="bvt_…"
            value={pastedKey}
            onChange={e => setPastedKey(e.target.value)}
            className="w-full bg-brand-bg border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-navy placeholder-brand-muted focus:outline-none focus:border-brand-blue transition-colors font-mono"
          />
          <button
            onClick={() => pastedKey.trim() && onSave(pastedKey.trim())}
            disabled={!pastedKey.trim()}
            className="w-full border border-brand-border hover:border-brand-navy text-brand-navy rounded-xl px-4 py-3 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Use this key
          </button>
        </div>

        {error && <p className="font-mono text-xs text-red-500">{error}</p>}
      </div>

      <p className="annotation mt-8 text-center">
        // start server first: <span className="text-brand-navy">uvicorn api.server:app --reload</span>
      </p>
    </div>
  )
}
