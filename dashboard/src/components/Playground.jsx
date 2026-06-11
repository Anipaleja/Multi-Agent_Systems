import { useState } from 'react'

const DEMO_MESSAGES = `The user needs a Python function that sorts a list of dictionaries by a given key.
The function should handle missing keys gracefully and support ascending and descending order.
We discussed earlier that the user prefers clean, readable code over one-liners.
The function should also handle missing keys gracefully with a default fallback value.`

const DEMO_CONTEXT = `User is working on a data processing pipeline in Python 3.11.
The project uses pandas for data manipulation and pytest for testing.
Previous agents have established that type hints are required on all functions.
The codebase follows PEP 8 style guidelines strictly.
User is working on a data processing pipeline in Python 3.11.`

function TokenBar({ baseline, optimized }) {
  const pct = baseline > 0 ? Math.max(4, Math.round((optimized / baseline) * 100)) : 50
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-400">
        <span>{baseline} tokens</span>
        <span className="text-violet-400 font-medium">{optimized} tokens</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-violet-600 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>Before</span>
        <span>After</span>
      </div>
    </div>
  )
}

function CodeBlock({ label, code }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">{label}</p>
        <button
          onClick={copy}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  )
}

export default function Playground({ apiKey }) {
  const [task, setTask]                     = useState('Write a Python sort utility function')
  const [messages, setMessages]             = useState(DEMO_MESSAGES)
  const [context, setContext]               = useState(DEMO_CONTEXT)
  const [complexity, setComplexity]         = useState(0.5)
  const [compressionLevel, setCompression]  = useState(2)
  const [pruneBudget, setPruneBudget]       = useState(5)
  const [loading, setLoading]               = useState(false)
  const [result, setResult]                 = useState(null)
  const [error, setError]                   = useState('')

  const run = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/v1/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({
          task,
          messages: messages.split('\n').map(s => s.trim()).filter(Boolean),
          prior_context: context.split('\n').map(s => s.trim()).filter(Boolean),
          complexity,
          compression_level: compressionLevel,
          prune_budget: pruneBudget,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const pythonSnippet = `import requests

def compress(messages, prior_context, task=""):
    r = requests.post(
        "http://localhost:8000/v1/compress",
        headers={"X-API-Key": "${apiKey}"},
        json={
            "messages": messages,
            "prior_context": prior_context,
            "task": task,
            "compression_level": ${compressionLevel},
            "prune_budget": ${pruneBudget},
        },
    )
    r.raise_for_status()
    d = r.json()
    # pass d["compressed_messages"] + d["pruned_context"]
    # to your next agent instead of the raw context
    print(f"Saved {d['savings_pct']}% tokens, quality {d['quality_proxy']*100:.1f}%")
    return d`

  const curlSnippet = `curl -X POST http://localhost:8000/v1/compress \\
  -H "X-API-Key: ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "task": "your task here",
    "messages": ["agent output 1", "agent output 2"],
    "prior_context": ["context chunk 1", "context chunk 2"],
    "compression_level": ${compressionLevel},
    "prune_budget": ${pruneBudget}
  }'`

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-2 gap-6">
        {/* ── Input ── */}
        <div className="space-y-4">
          <h2 className="font-semibold">Input</h2>

          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Current Task</label>
            <input
              value={task}
              onChange={e => setTask(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
              placeholder="Describe the current task…"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1.5">
              Agent Messages <span className="text-slate-600">(one per line)</span>
            </label>
            <textarea
              value={messages}
              onChange={e => setMessages(e.target.value)}
              rows={6}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500 font-mono resize-y transition-colors"
              placeholder="Paste agent messages here…"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1.5">
              Prior Context <span className="text-slate-600">(one per line)</span>
            </label>
            <textarea
              value={context}
              onChange={e => setContext(e.target.value)}
              rows={5}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500 font-mono resize-y transition-colors"
              placeholder="Prior context chunks…"
            />
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-4">
            <p className="text-xs font-medium text-slate-400">Settings</p>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Task Complexity</span>
                <span>{complexity.toFixed(1)}</span>
              </div>
              <input
                type="range" min="0" max="1" step="0.1" value={complexity}
                onChange={e => setComplexity(parseFloat(e.target.value))}
                className="w-full accent-violet-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Compression Level</label>
                <select
                  value={compressionLevel}
                  onChange={e => setCompression(Number(e.target.value))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-violet-500"
                >
                  <option value={1}>1 — Light</option>
                  <option value={2}>2 — Medium</option>
                  <option value={3}>3 — Aggressive</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Prune Budget</label>
                <select
                  value={pruneBudget}
                  onChange={e => setPruneBudget(Number(e.target.value))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-violet-500"
                >
                  <option value={3}>3 chunks</option>
                  <option value={5}>5 chunks</option>
                  <option value={8}>8 chunks</option>
                </select>
              </div>
            </div>
          </div>

          <button
            onClick={run}
            disabled={loading}
            className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded-lg px-4 py-3 text-sm font-medium transition-colors"
          >
            {loading ? 'Compressing…' : 'Compress →'}
          </button>
        </div>

        {/* ── Output ── */}
        <div className="space-y-4">
          <h2 className="font-semibold">Output</h2>

          {!result && !error && !loading && (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-16 text-center">
              <p className="text-slate-500 text-sm">Hit Compress to see results</p>
            </div>
          )}

          {loading && (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-16 text-center">
              <p className="text-slate-500 text-sm">Running pipeline…</p>
            </div>
          )}

          {error && (
            <div className="bg-red-950 border border-red-800 rounded-xl p-4 text-red-300 text-sm">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-emerald-950 border border-emerald-800 rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-emerald-400">{result.savings_pct.toFixed(1)}%</p>
                  <p className="text-emerald-700 text-xs mt-1">tokens saved</p>
                </div>
                <div className="bg-sky-950 border border-sky-800 rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-sky-400">
                    {(result.quality_proxy * 100).toFixed(1)}%
                  </p>
                  <p className="text-sky-700 text-xs mt-1">context retained</p>
                </div>
              </div>

              <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <p className="text-xs text-slate-400 mb-3">Token footprint</p>
                <TokenBar baseline={result.baseline_tokens} optimized={result.optimized_tokens} />
              </div>

              {result.compressed_messages?.length > 0 && (
                <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                  <p className="text-xs font-medium text-slate-400 mb-3">
                    Compressed Messages <span className="text-slate-600">({result.compressed_messages.length})</span>
                  </p>
                  <div className="space-y-2">
                    {result.compressed_messages.map((m, i) => (
                      <p key={i} className="text-xs text-slate-300 font-mono bg-slate-800 rounded-lg p-2.5 leading-relaxed">
                        {m}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {result.pruned_context?.length > 0 && (
                <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                  <p className="text-xs font-medium text-slate-400 mb-3">
                    Retained Context <span className="text-slate-600">({result.pruned_context.length})</span>
                  </p>
                  <div className="space-y-2">
                    {result.pruned_context.map((c, i) => (
                      <p key={i} className="text-xs text-slate-300 font-mono bg-slate-800 rounded-lg p-2.5 leading-relaxed">
                        {c}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <p className="text-xs text-slate-400">
                  Routed to <span className="text-violet-400 font-mono">{result.routed_model_hint}</span>
                  {result.state_id && (
                    <> · state <span className="font-mono text-slate-500">{result.state_id.slice(0, 14)}…</span></>
                  )}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Integration Guide ── */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 space-y-4">
        <div>
          <h3 className="font-semibold mb-1">Integration Guide</h3>
          <p className="text-slate-400 text-sm">
            Call <code className="bg-slate-800 px-1.5 py-0.5 rounded text-violet-300 text-xs">/v1/compress</code> before
            passing messages between agents. Feed{' '}
            <code className="bg-slate-800 px-1.5 py-0.5 rounded text-violet-300 text-xs">compressed_messages</code> +{' '}
            <code className="bg-slate-800 px-1.5 py-0.5 rounded text-violet-300 text-xs">pruned_context</code>{' '}
            into your next agent instead of the raw context.
          </p>
        </div>

        <CodeBlock label="Python" code={pythonSnippet} />
        <CodeBlock label="cURL" code={curlSnippet} />
      </div>
    </div>
  )
}
