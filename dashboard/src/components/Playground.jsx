import { useState } from 'react'

const DEMO_MESSAGES = `The user needs a Python function that sorts a list of dictionaries by a given key.
The function should handle missing keys gracefully and support ascending and descending order.
We discussed earlier that the user prefers clean, readable code over clever one-liners.
The function should also handle missing keys gracefully with a default fallback value.`

const DEMO_CONTEXT = `User is working on a data processing pipeline in Python 3.11.
The project uses pandas for data manipulation and pytest for testing.
Previous agents have established that type hints are required on all functions.
The codebase follows PEP 8 style guidelines strictly.
User is working on a data processing pipeline in Python 3.11.`

function Label({ children }) {
  return <p className="annotation mb-1.5">{children}</p>
}

function CodeBlock({ label, code }) {
  const [copied, setCopied] = useState(false)
  const copy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="annotation">{label}</p>
        <button onClick={copy} className="annotation hover:text-brand-navy transition-colors">
          {copied ? 'copied!' : 'copy'}
        </button>
      </div>
      <pre className="bg-brand-bg border border-brand-border rounded-xl p-5 text-xs font-mono text-brand-navy-mid overflow-x-auto leading-relaxed whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  )
}

function TokenBar({ baseline, optimized }) {
  const pct = baseline > 0 ? Math.max(4, Math.round((optimized / baseline) * 100)) : 50
  return (
    <div className="space-y-2">
      <div className="flex justify-between">
        <span className="font-mono text-xs text-brand-muted">{baseline} tokens</span>
        <span className="font-mono text-xs text-brand-blue font-medium">{optimized} tokens</span>
      </div>
      <div className="h-1.5 bg-brand-border rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-blue rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between annotation">
        <span>before</span><span>after</span>
      </div>
    </div>
  )
}

export default function Playground({ apiKey }) {
  const [task, setTask]                    = useState('Write a Python sort utility function')
  const [messages, setMessages]            = useState(DEMO_MESSAGES)
  const [context, setContext]              = useState(DEMO_CONTEXT)
  const [complexity, setComplexity]        = useState(0.5)
  const [compressionLevel, setCompression] = useState(2)
  const [pruneBudget, setPruneBudget]      = useState(5)
  const [loading, setLoading]              = useState(false)
  const [result, setResult]                = useState(null)
  const [error, setError]                  = useState('')

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await fetch('/v1/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({
          task,
          messages:      messages.split('\n').map(s => s.trim()).filter(Boolean),
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

  const pythonSnippet =
`import requests

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
    # to your next agent — not the raw context
    return d`

  const curlSnippet =
`curl -X POST http://localhost:8000/v1/compress \\
  -H "X-API-Key: ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "task": "your task here",
    "messages": ["agent output 1", "agent output 2"],
    "prior_context": ["context chunk 1"],
    "compression_level": ${compressionLevel},
    "prune_budget": ${pruneBudget}
  }'`

  return (
    <div className="space-y-14">
      {/* ── Hero text ── */}
      <div>
        <p className="annotation tracking-widest uppercase mb-4">Playground</p>
        <h2 className="font-serif text-4xl lg:text-5xl text-brand-navy leading-tight">
          Pick a task. Feed it to Brevitas.<br />
          <em className="italic text-brand-teal">Watch the tokens drop.</em>
        </h2>
        <p className="text-brand-muted text-base mt-4 max-w-lg leading-relaxed">
          Paste your agent messages and prior context below. The pipeline compresses, prunes, and
          references — your next agent gets only what it needs.
        </p>
      </div>

      {/* ── Input / Output grid ── */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Input */}
        <div className="space-y-5">
          <div>
            <Label>// current task</Label>
            <input
              value={task}
              onChange={e => setTask(e.target.value)}
              className="w-full bg-white border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-navy placeholder-brand-muted focus:outline-none focus:border-brand-blue transition-colors"
              placeholder="Describe the current task…"
            />
          </div>

          <div>
            <Label>// agent messages — one per line</Label>
            <textarea
              value={messages}
              onChange={e => setMessages(e.target.value)}
              rows={7}
              className="w-full bg-white border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-navy placeholder-brand-muted focus:outline-none focus:border-brand-blue font-mono resize-y transition-colors leading-relaxed"
            />
          </div>

          <div>
            <Label>// prior context — one per line</Label>
            <textarea
              value={context}
              onChange={e => setContext(e.target.value)}
              rows={5}
              className="w-full bg-white border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-navy placeholder-brand-muted focus:outline-none focus:border-brand-blue font-mono resize-y transition-colors leading-relaxed"
            />
          </div>

          {/* Settings */}
          <div className="bg-white border border-brand-border rounded-xl p-5 space-y-4">
            <p className="annotation">// settings</p>
            <div>
              <div className="flex justify-between annotation mb-2">
                <span>task complexity</span>
                <span className="text-brand-navy">{complexity.toFixed(1)}</span>
              </div>
              <input
                type="range" min="0" max="1" step="0.1" value={complexity}
                onChange={e => setComplexity(parseFloat(e.target.value))}
                className="w-full accent-brand-blue"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>// compression level</Label>
                <select
                  value={compressionLevel}
                  onChange={e => setCompression(Number(e.target.value))}
                  className="w-full bg-brand-bg border border-brand-border rounded-xl px-3 py-2.5 text-sm text-brand-navy focus:outline-none focus:border-brand-blue font-mono"
                >
                  <option value={1}>1 — light</option>
                  <option value={2}>2 — medium</option>
                  <option value={3}>3 — aggressive</option>
                </select>
              </div>
              <div>
                <Label>// prune budget</Label>
                <select
                  value={pruneBudget}
                  onChange={e => setPruneBudget(Number(e.target.value))}
                  className="w-full bg-brand-bg border border-brand-border rounded-xl px-3 py-2.5 text-sm text-brand-navy focus:outline-none focus:border-brand-blue font-mono"
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
            className="w-full bg-brand-blue hover:bg-brand-navy text-white rounded-xl px-4 py-3.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Running pipeline…' : 'Compress →'}
          </button>
        </div>

        {/* Output */}
        <div className="space-y-5">
          {!result && !error && !loading && (
            <div className="bg-white border border-brand-border rounded-2xl p-20 text-center h-full flex flex-col items-center justify-center">
              <p className="font-serif text-2xl text-brand-navy-mid mb-2">Results appear here.</p>
              <p className="annotation">// hit compress to run the pipeline</p>
            </div>
          )}

          {loading && (
            <div className="bg-white border border-brand-border rounded-2xl p-20 text-center h-full flex flex-col items-center justify-center">
              <p className="annotation">// running pipeline…</p>
            </div>
          )}

          {error && (
            <div className="bg-white border border-red-200 rounded-2xl p-5">
              <p className="font-mono text-xs text-red-500">{error}</p>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Big savings numbers */}
              <div className="bg-white border border-brand-border rounded-2xl p-7">
                <div className="grid grid-cols-2 gap-6 mb-7">
                  <div>
                    <p className="font-mono text-5xl font-medium text-brand-blue tabular-nums">
                      {result.savings_pct.toFixed(1)}%
                    </p>
                    <p className="annotation mt-1">// tokens saved</p>
                  </div>
                  <div>
                    <p className="font-mono text-5xl font-medium text-brand-teal tabular-nums">
                      {(result.quality_proxy * 100).toFixed(1)}%
                    </p>
                    <p className="annotation mt-1">// context retained</p>
                  </div>
                </div>
                <TokenBar baseline={result.baseline_tokens} optimized={result.optimized_tokens} />
              </div>

              {/* Compressed messages */}
              {result.compressed_messages?.length > 0 && (
                <div className="bg-white border border-brand-border rounded-2xl p-5">
                  <p className="annotation mb-3">
                    // compressed messages ({result.compressed_messages.length})
                  </p>
                  <div className="space-y-2">
                    {result.compressed_messages.map((m, i) => (
                      <p key={i} className="text-xs font-mono text-brand-navy-mid bg-brand-bg rounded-xl p-3 leading-relaxed">
                        {m}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {/* Retained context */}
              {result.pruned_context?.length > 0 && (
                <div className="bg-white border border-brand-border rounded-2xl p-5">
                  <p className="annotation mb-3">
                    // retained context ({result.pruned_context.length})
                  </p>
                  <div className="space-y-2">
                    {result.pruned_context.map((c, i) => (
                      <p key={i} className="text-xs font-mono text-brand-teal bg-brand-teal-dim rounded-xl p-3 leading-relaxed">
                        {c}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {/* Routing info */}
              <div className="bg-white border border-brand-border rounded-xl px-5 py-3">
                <p className="annotation">
                  routed → <span className="text-brand-blue">{result.routed_model_hint}</span>
                  {result.state_id && (
                    <> · state <span className="text-brand-muted">{result.state_id.slice(0, 14)}…</span></>
                  )}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Divider ── */}
      <div className="flex items-center gap-4">
        <div className="flex-1 h-px bg-brand-border" />
        <span className="annotation">// and no one optimized what flows between them</span>
        <div className="flex-1 h-px bg-brand-border" />
      </div>

      {/* ── Integration guide ── */}
      <div className="space-y-8">
        <div>
          <p className="annotation tracking-widest uppercase mb-2">Integration Guide</p>
          <p className="font-serif text-3xl text-brand-navy">
            Drop it in front of any agent hop.
          </p>
          <p className="text-brand-muted mt-3 text-sm leading-relaxed max-w-xl">
            Call <code className="font-mono text-brand-blue text-xs">/v1/compress</code> before
            passing messages between agents. Replace raw context with the returned{' '}
            <code className="font-mono text-brand-blue text-xs">compressed_messages</code> +{' '}
            <code className="font-mono text-brand-blue text-xs">pruned_context</code>.
            No changes to your agents, prompts, or provider.
          </p>
        </div>
        <CodeBlock label="// python" code={pythonSnippet} />
        <CodeBlock label="// curl"   code={curlSnippet}   />
      </div>
    </div>
  )
}
