import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './ResultsPanel.css'

/**
 * Final result summary (+ optional PageRank convergence chart).
 */
export default function ResultsPanel({ summary, convergenceHistory, algorithmId }) {
  if (!summary) {
    return (
      <section className="results-panel results-panel--empty">
        <p className="eyebrow">Results</p>
        <p className="muted">Run an algorithm to see the final answer here.</p>
      </section>
    )
  }

  const chartData = (convergenceHistory || []).map((delta, i) => ({
    iteration: i + 1,
    delta,
  }))

  return (
    <section className="results-panel">
      <p className="eyebrow">Results</p>
      <h3>{summary.title}</h3>
      <ul className="results-panel__lines">
        {summary.lines.map((line, i) => (
          <li key={`${i}-${line}`}>{line}</li>
        ))}
      </ul>

      {algorithmId === 'pagerank' && chartData.length > 1 && (
        <div className="results-panel__chart">
          <p className="section-label">PageRank convergence (L1 Δ)</p>
          <div className="results-panel__chart-frame">
            <ResponsiveContainer width="100%" height={160} minWidth={0}>
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#2a3646" strokeDasharray="3 3" />
                <XAxis
                  dataKey="iteration"
                  stroke="#8b9bb0"
                  tick={{ fill: '#8b9bb0', fontSize: 10 }}
                />
                <YAxis
                  stroke="#8b9bb0"
                  tick={{ fill: '#8b9bb0', fontSize: 10 }}
                  tickFormatter={(v) => Number(v).toExponential(0)}
                />
                <Tooltip
                  contentStyle={{
                    background: '#121820',
                    border: '1px solid #2a3646',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelFormatter={(v) => `Iteration ${v}`}
                  formatter={(value) => [Number(value).toExponential(3), 'L1 Δ']}
                />
                <Line
                  type="monotone"
                  dataKey="delta"
                  stroke="#c4a35a"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </section>
  )
}
