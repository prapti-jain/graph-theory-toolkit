import { useCallback, useEffect, useMemo, useState } from 'react'
import { getHealth } from './api/client'
import AlgorithmPanel from './components/AlgorithmPanel'
import GraphCanvas from './components/GraphCanvas'
import GraphInputPanel from './components/GraphInputPanel'
import ResultsPanel from './components/ResultsPanel'
import StepPlayer from './components/StepPlayer'
import useAlgorithmAnimation from './hooks/useAlgorithmAnimation'
import {
  buildAlgorithmBody,
  findAlgorithm,
  formatAlgorithmResult,
} from './utils/algorithms'
import './App.css'

const EMPTY_GRAPH = {
  name: 'Empty graph',
  directed: false,
  weighted: true,
  nodes: [],
  edges: [],
}

function App() {
  const [health, setHealth] = useState('checking')
  const [graph, setGraph] = useState(EMPTY_GRAPH)
  const [running, setRunning] = useState(false)
  const [steps, setSteps] = useState([])
  const [result, setResult] = useState(null)
  const [algorithmId, setAlgorithmId] = useState(null)
  const [runError, setRunError] = useState(null)

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data?.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => setHealth('down'))
  }, [])

  const animation = useAlgorithmAnimation({
    steps,
    graphEdges: graph.edges,
    directed: graph.directed,
  })

  const summary = useMemo(
    () => (result && algorithmId ? formatAlgorithmResult(algorithmId, result) : null),
    [result, algorithmId],
  )

  // Show summary once user reaches the end (or for algorithms with no steps).
  const resultsVisible =
    Boolean(summary) && (animation.atEnd || steps.length === 0)

  const handleGraphChange = useCallback((next) => {
    setGraph(next)
    setSteps([])
    setResult(null)
    setAlgorithmId(null)
    setRunError(null)
  }, [])

  const handleRun = useCallback(
    async (id, params) => {
      const algo = findAlgorithm(id)
      if (!algo) throw new Error(`Unknown algorithm ${id}`)

      setRunning(true)
      setRunError(null)
      try {
        const body = buildAlgorithmBody(graph, id, params)
        const data = await algo.run(body)
        const nextSteps = Array.isArray(data.steps) ? data.steps : []
        // Compare/MST may nest steps — flatten lightly if needed.
        const flatSteps =
          id === 'mst-compare'
            ? [
                ...(data.kruskals?.steps || []),
                ...(data.prims?.steps || []),
                ...(data.steps || []),
              ]
            : nextSteps

        setAlgorithmId(id)
        setResult(data)
        setSteps(flatSteps)
        if (flatSteps.length === 0) {
          // No animation — still show results immediately.
        }
      } catch (err) {
        setSteps([])
        setResult(null)
        setAlgorithmId(null)
        setRunError(err?.response?.data?.detail || err.message || 'Run failed')
        throw err
      } finally {
        setRunning(false)
      }
    },
    [graph],
  )

  return (
    <div className="shell">
      <header className="shell__top">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true" />
          <div>
            <p className="brand__eyebrow">Graph Theory Toolkit</p>
            <h1>Visualizer</h1>
          </div>
        </div>
        <div className={`health health--${health}`} title="Backend /health">
          <span className="health__dot" />
          <span className="health__label">
            {health === 'ok' && 'API online'}
            {health === 'checking' && 'Checking API…'}
            {health === 'degraded' && 'API degraded'}
            {health === 'down' && 'API offline'}
          </span>
        </div>
      </header>

      <div className="shell__body">
        <GraphInputPanel graph={graph} onGraphChange={handleGraphChange} />

        <main className="shell__main">
          <div className="canvas-toolbar">
            <div>
              <p className="canvas-toolbar__eyebrow">Canvas</p>
              <h2>{graph.name}</h2>
            </div>
            <p className="canvas-toolbar__flags">
              {graph.directed ? 'Directed' : 'Undirected'}
              {' · '}
              {graph.weighted ? 'Weighted' : 'Unweighted'}
              {algorithmId ? ` · ${findAlgorithm(algorithmId)?.label}` : ''}
            </p>
          </div>
          <GraphCanvas
            nodes={graph.nodes}
            edges={graph.edges}
            directed={graph.directed}
            weighted={graph.weighted}
            highlightedNodes={animation.highlightedNodes}
            highlightedEdges={animation.highlightedEdges}
            nodeHighlightRoles={animation.nodeHighlightRoles}
            edgeHighlightRoles={animation.edgeHighlightRoles}
          />
        </main>

        <aside className="shell__side">
          <AlgorithmPanel
            graph={graph}
            running={running}
            onRun={handleRun}
          />
          <StepPlayer
            index={animation.index}
            total={animation.total}
            playing={animation.playing}
            speed={animation.speed}
            disabled={!steps.length}
            currentStep={animation.currentStep}
            onPlay={animation.play}
            onPause={animation.pause}
            onToggle={animation.toggle}
            onStepForward={animation.stepForward}
            onStepBack={animation.stepBack}
            onReset={animation.reset}
            onGoToEnd={animation.goToEnd}
            onSpeedChange={animation.setSpeed}
          />
          <ResultsPanel
            summary={resultsVisible ? summary : null}
            convergenceHistory={result?.convergence_history}
            algorithmId={algorithmId}
          />
          {runError && <p className="side-error">{String(runError)}</p>}
          <div className="legend">
            <p className="eyebrow">Legend</p>
            <ul>
              <li><span className="swatch swatch--current" /> current</li>
              <li><span className="swatch swatch--visited" /> visited</li>
              <li><span className="swatch swatch--path" /> path / match</li>
              <li><span className="swatch swatch--mst" /> MST / flow</li>
              <li><span className="swatch swatch--result" /> result</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default App
