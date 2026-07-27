import { useEffect, useState } from 'react'
import { getHealth } from './api/client'
import GraphCanvas from './components/GraphCanvas'
import GraphInputPanel from './components/GraphInputPanel'
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

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data?.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => setHealth('down'))
  }, [])

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
        <GraphInputPanel graph={graph} onGraphChange={setGraph} />
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
            </p>
          </div>
          <GraphCanvas
            nodes={graph.nodes}
            edges={graph.edges}
            directed={graph.directed}
            weighted={graph.weighted}
          />
        </main>
      </div>
    </div>
  )
}

export default App
