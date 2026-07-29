import axios from 'axios'

/**
 * Shared HTTP client for the Graph Theory Toolkit backend.
 *
 * Production: set VITE_API_URL to the Render backend URL (no trailing slash).
 * Local default: http://localhost:8000
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

/** @typedef {string|number} NodeId */

/**
 * @typedef {Object} GraphPayload
 * @property {Array<Array<*>>} edges
 * @property {NodeId[]=} nodes
 * @property {boolean=} directed
 * @property {boolean=} weighted
 * @property {NodeId=} start
 * @property {NodeId=} goal
 * @property {NodeId=} source
 * @property {NodeId=} sink
 * @property {NodeId[]=} left_nodes
 * @property {NodeId[]=} right_nodes
 * @property {number=} damping
 * @property {number=} max_iterations
 * @property {number=} tolerance
 * @property {Record<string, number[]>=} coordinates
 */

export async function getHealth() {
  const { data } = await api.get('/health')
  return data
}

// --- Graphs / datasets -----------------------------------------------------

/**
 * @param {{
 *   type: 'random'|'grid',
 *   directed?: boolean,
 *   weighted?: boolean,
 *   n?: number,
 *   p?: number,
 *   rows?: number,
 *   cols?: number,
 *   min_weight?: number,
 *   max_weight?: number,
 * }} params
 */
export async function generateGraph(params) {
  const { data } = await api.post('/api/graphs/generate', params)
  return data
}

export async function loadKarateClub() {
  const { data } = await api.get('/api/datasets/karate-club')
  return data
}

export async function getBenchmarkResults() {
  const { data } = await api.get('/api/benchmarks/results')
  return data
}

// --- Traversal -------------------------------------------------------------

/** @param {GraphPayload} body */
export async function runBfs(body) {
  const { data } = await api.post('/api/traversal/bfs', body)
  return data
}

/** @param {GraphPayload} body */
export async function runDfs(body) {
  const { data } = await api.post('/api/traversal/dfs', body)
  return data
}

/** @param {GraphPayload} body */
export async function runScc(body) {
  const { data } = await api.post('/api/traversal/scc', body)
  return data
}

/** @param {GraphPayload} body */
export async function runBridges(body) {
  const { data } = await api.post('/api/traversal/bridges', body)
  return data
}

/** @param {GraphPayload} body */
export async function runArticulationPoints(body) {
  const { data } = await api.post('/api/traversal/articulation-points', body)
  return data
}

// --- Shortest paths --------------------------------------------------------

/** @param {GraphPayload} body */
export async function runDijkstra(body) {
  const { data } = await api.post('/api/shortest-path/dijkstra', body)
  return data
}

/** @param {GraphPayload} body */
export async function runBellmanFord(body) {
  const { data } = await api.post('/api/shortest-path/bellman-ford', body)
  return data
}

/** @param {GraphPayload} body */
export async function runFloydWarshall(body) {
  const { data } = await api.post('/api/shortest-path/floyd-warshall', body)
  return data
}

/** @param {GraphPayload} body */
export async function runAStar(body) {
  const { data } = await api.post('/api/shortest-path/a-star', body)
  return data
}

/** @param {GraphPayload} body */
export async function runJohnsons(body) {
  const { data } = await api.post('/api/shortest-path/johnsons', body)
  return data
}

// --- MST -------------------------------------------------------------------

/** @param {GraphPayload} body */
export async function runKruskals(body) {
  const { data } = await api.post('/api/mst/kruskals', body)
  return data
}

/** @param {GraphPayload} body */
export async function runPrims(body) {
  const { data } = await api.post('/api/mst/prims', body)
  return data
}

/** @param {GraphPayload} body */
export async function runMstCompare(body) {
  const { data } = await api.post('/api/mst/compare', body)
  return data
}

// --- Flows -----------------------------------------------------------------

/** @param {GraphPayload} body */
export async function runMaxFlow(body) {
  const { data } = await api.post('/api/flows/max-flow', body)
  return data
}

/** @param {GraphPayload} body */
export async function runMinCut(body) {
  const { data } = await api.post('/api/flows/min-cut', body)
  return data
}

/** @param {GraphPayload} body */
export async function runBipartiteMatching(body) {
  const { data } = await api.post('/api/flows/bipartite-matching', body)
  return data
}

/** @param {GraphPayload} body */
export async function runHopcroftKarp(body) {
  const { data } = await api.post('/api/flows/hopcroft-karp', body)
  return data
}

// --- Centrality ------------------------------------------------------------

/** @param {GraphPayload} body */
export async function runPagerank(body) {
  const { data } = await api.post('/api/centrality/pagerank', body)
  return data
}

/** @param {GraphPayload} body */
export async function runBetweenness(body) {
  const { data } = await api.post('/api/centrality/betweenness', body)
  return data
}

/** @param {GraphPayload} body */
export async function runCloseness(body) {
  const { data } = await api.post('/api/centrality/closeness', body)
  return data
}

/** @param {GraphPayload} body */
export async function runEigenvector(body) {
  const { data } = await api.post('/api/centrality/eigenvector', body)
  return data
}

export default api
