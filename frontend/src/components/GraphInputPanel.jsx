import { useMemo, useState } from 'react'
import { generateGraph, loadKarateClub } from '../api/client'
import './GraphInputPanel.css'

/**
 * Left-rail controls for building / loading graphs.
 *
 * @param {{
 *   graph: { nodes: Array, edges: Array, directed: boolean, weighted: boolean, name?: string },
 *   onGraphChange: (graph: object) => void,
 * }} props
 */
export default function GraphInputPanel({ graph, onGraphChange }) {
  const [mode, setMode] = useState('generate')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const [directed, setDirected] = useState(graph?.directed ?? false)
  const [weighted, setWeighted] = useState(graph?.weighted ?? true)

  const [genType, setGenType] = useState('random')
  const [n, setN] = useState(12)
  const [p, setP] = useState(0.28)
  const [rows, setRows] = useState(4)
  const [cols, setCols] = useState(4)

  const [nodeId, setNodeId] = useState('')
  const [edgeFrom, setEdgeFrom] = useState('')
  const [edgeTo, setEdgeTo] = useState('')
  const [edgeWeight, setEdgeWeight] = useState('1')

  const stats = useMemo(
    () => ({
      nodes: graph?.nodes?.length ?? 0,
      edges: graph?.edges?.length ?? 0,
      name: graph?.name ?? 'Untitled graph',
    }),
    [graph],
  )

  const applyFlags = (next) => {
    onGraphChange({
      ...next,
      directed: Boolean(next.directed),
      weighted: Boolean(next.weighted),
    })
  }

  const updateFlags = (nextDirected, nextWeighted) => {
    setDirected(nextDirected)
    setWeighted(nextWeighted)
    if (graph) {
      const nextEdges = (graph.edges || []).map((e) => ({
        ...e,
        // Switching to unweighted forces unit weights so canvas/API stay consistent.
        weight: nextWeighted ? e.weight ?? 1 : 1,
        directed: nextDirected,
      }))
      onGraphChange({
        ...graph,
        directed: nextDirected,
        weighted: nextWeighted,
        edges: nextEdges,
      })
    }
  }

  const handleGenerate = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await generateGraph({
        type: genType,
        directed: genType === 'grid' ? false : directed,
        weighted: genType === 'grid' ? false : weighted,
        n: Number(n),
        p: Number(p),
        rows: Number(rows),
        cols: Number(cols),
        min_weight: 1,
        max_weight: 10,
      })
      applyFlags(normalizeApiGraph(data))
      if (genType === 'grid') {
        setDirected(false)
        setWeighted(false)
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Generate failed')
    } finally {
      setBusy(false)
    }
  }

  const handleLoadKarate = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await loadKarateClub()
      const normalized = normalizeApiGraph(data)
      setDirected(false)
      setWeighted(false)
      applyFlags(normalized)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Load failed')
    } finally {
      setBusy(false)
    }
  }

  const handleAddNode = (event) => {
    event.preventDefault()
    const id = coerceId(nodeId)
    if (id === '' || id == null) {
      setError('Enter a node id')
      return
    }
    const existing = graph?.nodes ?? []
    if (existing.some((n) => String(n.id) === String(id))) {
      setError(`Node ${id} already exists`)
      return
    }
    setError(null)
    applyFlags({
      name: graph?.name ?? 'Manual graph',
      directed,
      weighted,
      nodes: [...existing, { id, label: String(id) }],
      edges: graph?.edges ?? [],
    })
    setNodeId('')
  }

  const handleAddEdge = (event) => {
    event.preventDefault()
    const from = coerceId(edgeFrom)
    const to = coerceId(edgeTo)
    if (from === '' || from == null || to === '' || to == null) {
      setError('Edge needs from and to')
      return
    }
    let nodes = [...(graph?.nodes ?? [])]
    const ensure = (id) => {
      if (!nodes.some((n) => String(n.id) === String(id))) {
        nodes.push({ id, label: String(id) })
      }
    }
    ensure(from)
    ensure(to)
    const weight = weighted ? Number(edgeWeight) || 1 : 1
    const edges = [
      ...(graph?.edges ?? []),
      {
        id: `e-${from}-${to}-${Date.now()}`,
        from,
        to,
        weight,
        directed,
      },
    ]
    setError(null)
    applyFlags({
      name: graph?.name ?? 'Manual graph',
      directed,
      weighted,
      nodes,
      edges,
    })
    setEdgeFrom('')
    setEdgeTo('')
  }

  const handleClear = () => {
    setError(null)
    applyFlags({
      name: 'Empty graph',
      directed,
      weighted,
      nodes: [],
      edges: [],
    })
  }

  return (
    <aside className="input-panel">
      <header className="input-panel__header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Graph input</h2>
        </div>
        <p className="input-panel__meta">
          {stats.nodes} nodes · {stats.edges} edges
        </p>
      </header>

      <section className="input-panel__section">
        <p className="section-label">Graph mode</p>
        <div className="toggle-row">
          <button
            type="button"
            className={directed ? 'chip chip--active' : 'chip'}
            onClick={() => updateFlags(true, weighted)}
          >
            Directed
          </button>
          <button
            type="button"
            className={!directed ? 'chip chip--active' : 'chip'}
            onClick={() => updateFlags(false, weighted)}
          >
            Undirected
          </button>
        </div>
        <div className="toggle-row">
          <button
            type="button"
            className={weighted ? 'chip chip--active' : 'chip'}
            onClick={() => updateFlags(directed, true)}
          >
            Weighted
          </button>
          <button
            type="button"
            className={!weighted ? 'chip chip--active' : 'chip'}
            onClick={() => updateFlags(directed, false)}
          >
            Unweighted
          </button>
        </div>
      </section>

      <nav className="mode-tabs" aria-label="Input mode">
        {[
          ['generate', 'Generate'],
          ['manual', 'Manual'],
          ['preset', 'Preset'],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={mode === id ? 'mode-tabs__btn mode-tabs__btn--active' : 'mode-tabs__btn'}
            onClick={() => setMode(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {mode === 'generate' && (
        <section className="input-panel__section stack">
          <label className="field">
            <span>Type</span>
            <select value={genType} onChange={(e) => setGenType(e.target.value)}>
              <option value="random">Random (Erdős–Rényi)</option>
              <option value="grid">Grid</option>
            </select>
          </label>

          {genType === 'random' ? (
            <>
              <label className="field">
                <span>Nodes (n)</span>
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={n}
                  onChange={(e) => setN(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Edge probability (p)</span>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={p}
                  onChange={(e) => setP(e.target.value)}
                />
              </label>
            </>
          ) : (
            <div className="field-row">
              <label className="field">
                <span>Rows</span>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={rows}
                  onChange={(e) => setRows(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Cols</span>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={cols}
                  onChange={(e) => setCols(e.target.value)}
                />
              </label>
            </div>
          )}

          <button
            type="button"
            className="btn btn--primary"
            disabled={busy}
            onClick={handleGenerate}
          >
            {busy ? 'Generating…' : 'Generate graph'}
          </button>
          {genType === 'grid' && (
            <p className="hint">Grid graphs are undirected and unweighted.</p>
          )}
        </section>
      )}

      {mode === 'manual' && (
        <section className="input-panel__section stack">
          <form className="stack" onSubmit={handleAddNode}>
            <label className="field">
              <span>Node id</span>
              <input
                value={nodeId}
                onChange={(e) => setNodeId(e.target.value)}
                placeholder="e.g. 0 or A"
              />
            </label>
            <button type="submit" className="btn">
              Add node
            </button>
          </form>

          <form className="stack" onSubmit={handleAddEdge}>
            <div className="field-row">
              <label className="field">
                <span>From</span>
                <input value={edgeFrom} onChange={(e) => setEdgeFrom(e.target.value)} />
              </label>
              <label className="field">
                <span>To</span>
                <input value={edgeTo} onChange={(e) => setEdgeTo(e.target.value)} />
              </label>
            </div>
            {weighted && (
              <label className="field">
                <span>Weight</span>
                <input
                  type="number"
                  step="any"
                  value={edgeWeight}
                  onChange={(e) => setEdgeWeight(e.target.value)}
                />
              </label>
            )}
            <button type="submit" className="btn">
              Add edge
            </button>
          </form>
        </section>
      )}

      {mode === 'preset' && (
        <section className="input-panel__section stack">
          <article className="preset-card">
            <h3>Zachary&apos;s Karate Club</h3>
            <p>Classic 34-node social network. Useful for centrality demos.</p>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy}
              onClick={handleLoadKarate}
            >
              {busy ? 'Loading…' : 'Load dataset'}
            </button>
          </article>
        </section>
      )}

      <footer className="input-panel__footer">
        <div>
          <p className="eyebrow">Active</p>
          <p className="input-panel__active-name">{stats.name}</p>
        </div>
        <button type="button" className="btn btn--ghost" onClick={handleClear}>
          Clear
        </button>
      </footer>

      {error && <p className="input-panel__error">{String(error)}</p>}
    </aside>
  )
}

function normalizeApiGraph(data) {
  const directed = Boolean(data.directed)
  const weighted = Boolean(data.weighted)
  return {
    name: data.name || 'Loaded graph',
    directed,
    weighted,
    nodes: (data.nodes || []).map((n) => ({
      id: n.id,
      label: n.label != null ? String(n.label) : String(n.id),
      club: n.club,
    })),
    edges: (data.edges || []).map((e, i) => ({
      id: `e-${e.u}-${e.v}-${i}`,
      from: e.u,
      to: e.v,
      // Unweighted graphs always use unit weight; never keep random leftovers.
      weight: weighted ? Number(e.weight ?? 1) : 1,
      directed,
    })),
  }
}

function coerceId(raw) {
  const trimmed = String(raw).trim()
  if (!trimmed) return ''
  if (/^-?\d+$/.test(trimmed)) return Number(trimmed)
  return trimmed
}
