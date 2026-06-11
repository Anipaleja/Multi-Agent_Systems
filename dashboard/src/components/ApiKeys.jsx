import { useState, useEffect } from 'react'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={copy}
      className="shrink-0 bg-slate-700 hover:bg-slate-600 rounded px-3 py-1.5 text-xs transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

export default function ApiKeys({ apiKey }) {
  const [keys, setKeys]       = useState([])
  const [name, setName]       = useState('')
  const [newKey, setNewKey]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const loadKeys = async () => {
    try {
      const res = await fetch('/v1/keys', { headers: { 'X-API-Key': apiKey } })
      if (res.ok) setKeys((await res.json()).keys ?? [])
    } catch {}
  }

  useEffect(() => { loadKeys() }, [apiKey])

  const create = async () => {
    setLoading(true)
    setError('')
    setNewKey('')
    try {
      const res = await fetch('/v1/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() || 'unnamed' }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setNewKey(data.api_key)
      setName('')
      await loadKeys()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-5">
      <h2 className="font-semibold">API Keys</h2>

      {/* Create */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
        <h3 className="text-sm font-medium mb-3">Create a new key</h3>
        <div className="flex gap-3">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && create()}
            placeholder="Project name"
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
          />
          <button
            onClick={create}
            disabled={loading}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors whitespace-nowrap"
          >
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>

        {newKey && (
          <div className="mt-3 bg-emerald-950 border border-emerald-800 rounded-lg p-4">
            <p className="text-xs text-emerald-400 mb-2">
              New key created — copy it now, it won't be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono text-emerald-300 break-all">{newKey}</code>
              <CopyButton text={newKey} />
            </div>
          </div>
        )}

        {error && <p className="mt-2 text-red-400 text-xs">{error}</p>}
      </div>

      {/* Existing keys */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
        <h3 className="text-sm font-medium mb-3">Existing keys</h3>
        {keys.length === 0 ? (
          <p className="text-slate-500 text-sm">No keys yet.</p>
        ) : (
          <div className="space-y-2">
            {keys.map((k, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-800 rounded-lg px-4 py-3">
                <div>
                  <p className="text-sm font-medium">{k.name}</p>
                  <p className="text-xs text-slate-500">
                    Created {new Date(k.created).toLocaleDateString('en-US', {
                      year: 'numeric', month: 'short', day: 'numeric',
                    })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Current key */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
        <h3 className="text-sm font-medium mb-3">Active session key</h3>
        <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-3">
          <code className="flex-1 text-xs font-mono text-slate-400 truncate">{apiKey}</code>
          <CopyButton text={apiKey} />
        </div>
      </div>

      {/* Quick reference */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 space-y-3">
        <h3 className="text-sm font-medium">API Reference</h3>
        <div className="space-y-2 text-xs font-mono">
          {[
            ['POST', '/v1/compress', 'Compress messages + context'],
            ['GET',  '/v1/stats',    'Usage stats for this key'],
            ['POST', '/v1/keys',     'Create a new API key'],
            ['GET',  '/v1/health',   'Server health check'],
          ].map(([method, path, desc]) => (
            <div key={path} className="flex items-center gap-3 text-slate-400">
              <span className={`w-10 text-center rounded px-1 py-0.5 text-xs font-bold ${
                method === 'POST' ? 'bg-violet-900 text-violet-300' : 'bg-sky-900 text-sky-300'
              }`}>
                {method}
              </span>
              <span className="text-slate-300">{path}</span>
              <span className="text-slate-600 hidden sm:block">— {desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
