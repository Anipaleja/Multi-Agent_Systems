import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area,
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts'

const fmt = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))

const tooltipStyle = {
  contentStyle: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e4f0',
    borderRadius: 10,
    fontSize: 12,
    color: '#0d1530',
    boxShadow: '0 4px 16px rgba(13,21,48,0.08)',
  },
  labelStyle: { color: '#8b93b8', fontFamily: 'JetBrains Mono' },
}

function BigStat({ value, label, valueClass = 'text-brand-navy' }) {
  return (
    <div className="text-center">
      <p className={`font-mono text-4xl lg:text-5xl font-medium tabular-nums ${valueClass}`}>
        {value}
      </p>
      <p className="annotation mt-2">{label}</p>
    </div>
  )
}

export default function Overview({ apiKey }) {
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  const loadStats = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/v1/stats', { headers: { 'X-API-Key': apiKey } })
      if (!res.ok) throw new Error('Failed to load stats')
      setStats(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { loadStats() }, [loadStats])

  if (loading) return <p className="annotation pt-8">// loading…</p>
  if (error)   return <p className="font-mono text-xs text-red-500 pt-8">{error}</p>

  const chartData = [...(stats?.history ?? [])]
    .reverse()
    .slice(-20)
    .map((h, i) => ({
      call: i + 1,
      savings:   parseFloat(h.savings_pct.toFixed(1)),
      baseline:  h.baseline_tokens,
      optimized: h.optimized_tokens,
    }))

  return (
    <div className="space-y-16">
      {/* ── Section label ── */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="annotation tracking-widest uppercase">Dashboard metrics — 2026</p>
          <button
            onClick={loadStats}
            className="annotation hover:text-brand-navy transition-colors"
          >
            refresh
          </button>
        </div>
        <div className="h-px bg-brand-border" />
      </div>

      {/* ── Big stats row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-4">
        <BigStat value={stats.total_calls}              label="// api calls" />
        <BigStat value={fmt(stats.total_tokens_saved)}  label="// tokens saved"   valueClass="text-brand-blue" />
        <BigStat value={`${stats.avg_savings_pct.toFixed(1)}%`} label="// avg savings"  valueClass="text-brand-blue" />
        <BigStat
          value={`${(stats.avg_quality_proxy * 100).toFixed(1)}%`}
          label="// context retained"
          valueClass="text-brand-teal"
        />
      </div>

      {/* ── Token flow summary ── */}
      {stats.total_calls > 0 && (
        <div className="text-center space-y-2">
          <p className="font-serif text-2xl text-brand-navy-mid">
            {fmt(stats.total_baseline_tokens)} tokens in,{' '}
            <em className="font-serif italic text-brand-blue">{fmt(stats.total_optimized_tokens)} out.</em>
          </p>
          <p className="annotation">// first-run benchmark · real api calls</p>
        </div>
      )}

      {chartData.length === 0 ? (
        <div className="bg-white rounded-2xl border border-brand-border p-20 text-center">
          <p className="font-serif text-2xl text-brand-navy-mid mb-3">No data yet.</p>
          <p className="annotation">
            // run a compression from the{' '}
            <span className="text-brand-navy">Playground</span> tab to see charts
          </p>
        </div>
      ) : (
        <>
          {/* ── Savings chart ── */}
          <div className="bg-white rounded-2xl border border-brand-border p-8">
            <p className="annotation tracking-widest uppercase mb-1">Savings %</p>
            <p className="font-serif text-xl text-brand-navy mb-6">
              last {chartData.length} calls
            </p>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 16 }}>
                <defs>
                  <linearGradient id="gBlue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#4f5fc4" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#4f5fc4" stopOpacity={0}    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e4f0" />
                <XAxis
                  dataKey="call"
                  tick={{ fill: '#8b93b8', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  label={{ value: 'call #', position: 'insideBottom', offset: -10, fill: '#c4c8e2', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: '#8b93b8', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  tickFormatter={v => `${v}%`}
                />
                <Tooltip {...tooltipStyle} formatter={v => [`${v}%`, 'savings']} />
                <Area
                  type="monotone"
                  dataKey="savings"
                  stroke="#4f5fc4"
                  fill="url(#gBlue)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: '#4f5fc4', strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* ── Token comparison chart ── */}
          <div className="bg-white rounded-2xl border border-brand-border p-8">
            <p className="annotation tracking-widest uppercase mb-1">Token footprint</p>
            <p className="font-serif text-xl text-brand-navy mb-6">
              baseline <em className="italic text-brand-blue">vs</em> optimized
            </p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} barGap={2} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e4f0" />
                <XAxis
                  dataKey="call"
                  tick={{ fill: '#8b93b8', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                />
                <YAxis
                  tick={{ fill: '#8b93b8', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  tickFormatter={fmt}
                />
                <Tooltip {...tooltipStyle} />
                <Legend
                  wrapperStyle={{ fontSize: 11, color: '#8b93b8', fontFamily: 'JetBrains Mono' }}
                />
                <Bar dataKey="baseline"  name="baseline"  fill="#e2e4f0" radius={[4, 4, 0, 0]} />
                <Bar dataKey="optimized" name="optimized" fill="#4f5fc4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
