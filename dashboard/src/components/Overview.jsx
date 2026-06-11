import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area,
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'

const fmt = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))

function StatCard({ label, value, sub, valueClass = 'text-slate-100' }) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      <p className={`text-3xl font-bold ${valueClass}`}>{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}

const tooltipStyle = {
  contentStyle: { backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#94a3b8' },
}

export default function Overview({ apiKey }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  if (loading) return <p className="text-slate-400 text-sm">Loading…</p>
  if (error)   return <p className="text-red-400 text-sm">{error}</p>

  const chartData = [...(stats?.history ?? [])]
    .reverse()
    .slice(-20)
    .map((h, i) => ({
      call: i + 1,
      savings: parseFloat(h.savings_pct.toFixed(1)),
      baseline: h.baseline_tokens,
      optimized: h.optimized_tokens,
    }))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Overview</h2>
        <button
          onClick={loadStats}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="API Calls"      value={stats.total_calls} />
        <StatCard
          label="Tokens Saved"
          value={fmt(stats.total_tokens_saved)}
          sub={`${fmt(stats.total_baseline_tokens)} → ${fmt(stats.total_optimized_tokens)}`}
          valueClass="text-emerald-400"
        />
        <StatCard
          label="Avg Savings"
          value={`${stats.avg_savings_pct.toFixed(1)}%`}
          valueClass="text-violet-400"
        />
        <StatCard
          label="Context Quality"
          value={`${(stats.avg_quality_proxy * 100).toFixed(1)}%`}
          sub="avg retained"
          valueClass="text-sky-400"
        />
      </div>

      {chartData.length === 0 ? (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-16 text-center">
          <p className="text-slate-500 text-sm">
            No data yet — run a compression from the <strong className="text-slate-400">Playground</strong> tab.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <p className="text-sm font-medium text-slate-300 mb-4">
              Savings % — last {chartData.length} calls
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 16 }}>
                <defs>
                  <linearGradient id="gSavings" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="call"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  label={{ value: 'Call #', position: 'insideBottom', offset: -10, fill: '#475569', fontSize: 11 }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickFormatter={v => `${v}%`}
                />
                <Tooltip {...tooltipStyle} formatter={v => [`${v}%`, 'Savings']} />
                <Area
                  type="monotone"
                  dataKey="savings"
                  stroke="#8b5cf6"
                  fill="url(#gSavings)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: '#8b5cf6' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <p className="text-sm font-medium text-slate-300 mb-4">
              Baseline vs Optimized tokens — last {chartData.length} calls
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barGap={2} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="call" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={fmt} />
                <Tooltip {...tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                <Bar dataKey="baseline"  name="Baseline"  fill="#334155" radius={[3, 3, 0, 0]} />
                <Bar dataKey="optimized" name="Optimized" fill="#7c3aed" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
