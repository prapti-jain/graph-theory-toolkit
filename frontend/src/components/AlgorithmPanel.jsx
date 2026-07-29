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
  const [leftNodes, setLeftNodes] = useState([])
  const [rightNodes, setRightNodes] = useState([])
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
    if (needs.includes('goal') && !algorithm.goalOptional && goal === '') {
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
    if (needs.includes('leftRight')) {
      if (!leftNodes.length || !rightNodes.length) {
        setError('Assign at least one node to Left and one to Right')
        return
      }
      const overlap = leftNodes.filter((id) =>
        rightNodes.some((r) => String(r) === String(id)),
      )
      if (overlap.length) {
        setError('Left and Right sets must be disjoint')
        return
      }
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
            label={algorithm.goalOptional ? 'Goal node (optional)' : 'Goal node'}
            value={goal}
            onChange={setGoal}
            options={nodeOptions}
            allowEmpty={Boolean(algorithm.goalOptional)}
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
          <PartitionPicker
            nodes={nodeOptions}
            left={leftNodes}
            right={rightNodes}
            onChange={(nextLeft, nextRight) => {
              setLeftNodes(nextLeft)
              setRightNodes(nextRight)
            }}
          />
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

/**
 * Click-to-assign bipartition UI: each node cycles Unassigned → Left → Right.
 */
function PartitionPicker({ nodes, left, right, onChange }) {
  const leftSet = useMemo(
    () => new Set(left.map((id) => String(id))),
    [left],
  )
  const rightSet = useMemo(
    () => new Set(right.map((id) => String(id))),
    [right],
  )

  const sideOf = (id) => {
    const key = String(id)
    if (leftSet.has(key)) return 'left'
    if (rightSet.has(key)) return 'right'
    return 'none'
  }

  const cycle = (id) => {
    const key = String(id)
    const without = (arr) => arr.filter((x) => String(x) !== key)
    const side = sideOf(id)
    if (side === 'none') {
      onChange([...left, id], without(right))
    } else if (side === 'left') {
      onChange(without(left), [...without(right), id])
    } else {
      onChange(without(left), without(right))
    }
  }

  const splitEvenly = () => {
    const mid = Math.ceil(nodes.length / 2)
    onChange(nodes.slice(0, mid), nodes.slice(mid))
  }

  const clear = () => onChange([], [])

  return (
    <div className="partition">
      <div className="partition__header">
        <span className="field-label">Bipartition</span>
        <div className="partition__actions">
          <button type="button" className="btn btn--ghost btn--tiny" onClick={splitEvenly}>
            Split evenly
          </button>
          <button type="button" className="btn btn--ghost btn--tiny" onClick={clear}>
            Clear
          </button>
        </div>
      </div>
      <p className="hint">
        Click a node to cycle: unassigned → Left → Right. Matching needs both
        sets non-empty and disjoint.
      </p>
      <div className="partition__chips" role="group" aria-label="Assign nodes to Left or Right">
        {nodes.length === 0 ? (
          <p className="muted">Load a graph to assign nodes.</p>
        ) : (
          nodes.map((id) => {
            const side = sideOf(id)
            return (
              <button
                key={String(id)}
                type="button"
                className={`partition__chip partition__chip--${side}`}
                onClick={() => cycle(id)}
                title={
                  side === 'none'
                    ? 'Unassigned — click for Left'
                    : side === 'left'
                      ? 'Left — click for Right'
                      : 'Right — click to clear'
                }
              >
                <span className="partition__chip-side">
                  {side === 'left' ? 'L' : side === 'right' ? 'R' : '·'}
                </span>
                {String(id)}
              </button>
            )
          })
        )}
      </div>
      <div className="partition__summary">
        <span>
          Left ({left.length}): {left.map(String).join(', ') || '—'}
        </span>
        <span>
          Right ({right.length}): {right.map(String).join(', ') || '—'}
        </span>
      </div>
    </div>
  )
}
