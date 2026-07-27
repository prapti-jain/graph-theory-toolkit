import { useMemo, useState } from 'react'
import { ALGORITHM_CATEGORIES, findAlgorithm } from '../utils/algorithms'
import './AlgorithmPanel.css'

/**
 * Algorithm picker + parameter form + Run button.
 */
export default function AlgorithmPanel({
  graph,
  disabled = false,
  running = false,
  onRun,
}) {
  const [categoryId, setCategoryId] = useState('traversal')
  const [algorithmId, setAlgorithmId] = useState('bfs')
  const [start, setStart] = useState('')
  const [goal, setGoal] = useState('')
  const [source, setSource] = useState('')
  const [sink, setSink] = useState('')
  const [leftNodes, setLeftNodes] = useState('')
  const [rightNodes, setRightNodes] = useState('')
  const [error, setError] = useState(null)

  const category = ALGORITHM_CATEGORIES.find((c) => c.id === categoryId)
  const algorithm = findAlgorithm(algorithmId)
  const nodeOptions = useMemo(
    () => (graph?.nodes || []).map((n) => n.id),
    [graph],
  )

  const selectCategory = (id) => {
    setCategoryId(id)
    const first = ALGORITHM_CATEGORIES.find((c) => c.id === id)?.algorithms[0]
    if (first) setAlgorithmId(first.id)
    setError(null)
  }

  const handleRun = async () => {
    setError(null)
    if (!graph?.nodes?.length) {
      setError('Load or generate a graph first')
      return
    }
    const needs = algorithm?.needs || []
    if (needs.includes('start') && !algorithm.startOptional && start === '') {
      setError('Start node is required')
      return
    }
    if (needs.includes('goal') && goal === '') {
      setError('Goal node is required')
      return
    }
    if (needs.includes('source') && source === '') {
      setError('Source node is required')
      return
    }
    if (needs.includes('sink') && sink === '') {
      setError('Sink node is required')
      return
    }
    if (needs.includes('leftRight') && (!leftNodes.trim() || !rightNodes.trim())) {
      setError('Provide left_nodes and right_nodes (comma-separated)')
      return
    }

    try {
      await onRun(algorithmId, {
        start,
        goal,
        source,
        sink,
        leftNodes,
        rightNodes,
      })
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Run failed')
    }
  }

  return (
    <section className="algo-panel">
      <header className="algo-panel__header">
        <p className="eyebrow">Execute</p>
        <h2>Algorithm</h2>
      </header>

      <div className="algo-cats" role="tablist" aria-label="Algorithm categories">
        {ALGORITHM_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            type="button"
            role="tab"
            aria-selected={categoryId === cat.id}
            className={
              categoryId === cat.id
                ? 'algo-cats__btn algo-cats__btn--active'
                : 'algo-cats__btn'
            }
            onClick={() => selectCategory(cat.id)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <label className="field">
        <span>Method</span>
        <select
          value={algorithmId}
          onChange={(e) => {
            setAlgorithmId(e.target.value)
            setError(null)
          }}
        >
          {(category?.algorithms || []).map((a) => (
            <option key={a.id} value={a.id}>
              {a.label}
            </option>
          ))}
        </select>
      </label>

      <div className="algo-params stack">
        {algorithm?.needs?.includes('start') && (
          <NodeSelect
            label={algorithm.startOptional ? 'Start (optional)' : 'Start node'}
            value={start}
            onChange={setStart}
            options={nodeOptions}
            allowEmpty={Boolean(algorithm.startOptional)}
          />
        )}
        {algorithm?.needs?.includes('goal') && (
          <NodeSelect
            label="Goal node"
            value={goal}
            onChange={setGoal}
            options={nodeOptions}
          />
        )}
        {algorithm?.needs?.includes('source') && (
          <NodeSelect
            label="Source"
            value={source}
            onChange={setSource}
            options={nodeOptions}
          />
        )}
        {algorithm?.needs?.includes('sink') && (
          <NodeSelect
            label="Sink"
            value={sink}
            onChange={setSink}
            options={nodeOptions}
          />
        )}
        {algorithm?.needs?.includes('leftRight') && (
          <>
            <label className="field">
              <span>Left nodes</span>
              <input
                value={leftNodes}
                onChange={(e) => setLeftNodes(e.target.value)}
                placeholder="0, 1, 2"
              />
            </label>
            <label className="field">
              <span>Right nodes</span>
              <input
                value={rightNodes}
                onChange={(e) => setRightNodes(e.target.value)}
                placeholder="3, 4, 5"
              />
            </label>
          </>
        )}
        {algorithm?.needs?.includes('coords') && (
          <p className="hint">
            A* uses circular layout coordinates derived from node indices.
          </p>
        )}
        {algorithm?.preferDirected && !graph?.directed && (
          <p className="hint warn">Works best on a directed graph.</p>
        )}
        {algorithm?.preferUndirected && graph?.directed && (
          <p className="hint warn">Requires an undirected graph.</p>
        )}
      </div>

      <button
        type="button"
        className="btn btn--primary"
        disabled={disabled || running || !graph?.nodes?.length}
        onClick={handleRun}
      >
        {running ? 'Running…' : 'Run algorithm'}
      </button>

      {error && <p className="algo-panel__error">{String(error)}</p>}
    </section>
  )
}

function NodeSelect({ label, value, onChange, options, allowEmpty = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{allowEmpty ? '— auto —' : 'Select…'}</option>
        {options.map((id) => (
          <option key={String(id)} value={String(id)}>
            {String(id)}
          </option>
        ))}
      </select>
    </label>
  )
}
