# Graph Theory Toolkit

From-scratch implementations of classical graph algorithms, validated against NetworkX, with an interactive step-by-step visualizer and an empirical complexity-benchmarking harness.

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://graph-theory-toolkit.vercel.app)
[![API](https://img.shields.io/badge/API-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://graph-theory-toolkit.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](backend/)
[![React](https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](frontend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)](backend/)

| | |
|---|---|
| **Live demo** | https://graph-theory-toolkit.vercel.app |
| **Backend API** | https://graph-theory-toolkit.onrender.com |
| **Health check** | https://graph-theory-toolkit.onrender.com/health |

> **Note:** The Render free tier may cold-start after idle (~30–60s on first request).

---

## Features

- **20+ algorithms** across traversal, shortest paths, MST, flows/matching, and centrality
- **Interactive canvas** — generate, edit, or load graphs (including Zachary’s Karate Club); animate algorithm steps
- **NetworkX-backed tests** — implementations are independent; NetworkX is used only as a correctness oracle and dataset source
- **Complexity benchmarks** — empirical runtime curves fitted against claimed asymptotic bounds
- **Deployed end-to-end** — React UI on Vercel, FastAPI on Render

## Algorithms

| Category | Algorithms |
|----------|------------|
| **Traversal / connectivity** | BFS, DFS, Topological Sort, Tarjan’s SCC, Bridges, Articulation Points |
| **Shortest paths** | Dijkstra, Bellman–Ford, Floyd–Warshall, A*, Johnson’s |
| **Minimum spanning trees** | Kruskal’s, Prim’s |
| **Flows / matching** | Edmonds–Karp Max-Flow, Min-Cut, Bipartite Matching, Hopcroft–Karp |
| **Centrality** | PageRank, Betweenness, Closeness, Eigenvector |

## Tech Stack

| Layer | Technologies |
|-------|----------------|
| **Backend** | Python, FastAPI, uvicorn · NetworkX (validation / Karate Club only) · pytest · NumPy / SciPy |
| **Frontend** | React, Vite · vis-network · Recharts · Axios |
| **Deployment** | [Render](https://graph-theory-toolkit.onrender.com) (API) · [Vercel](https://graph-theory-toolkit.vercel.app) (UI) |

## Deployment

| Service | URL | Role |
|---------|-----|------|
| **Vercel** | https://graph-theory-toolkit.vercel.app | Frontend (`frontend/`, Vite build) |
| **Render** | https://graph-theory-toolkit.onrender.com | Backend (`backend/`, `uvicorn main:app`) |

**Environment (production)**

| Variable | Where | Purpose |
|----------|--------|---------|
| `VITE_API_URL` | Vercel | API base URL → `https://graph-theory-toolkit.onrender.com` |
| `CORS_ORIGINS` | Render | Allowed browser origins (comma-separated); `*.vercel.app` also allowed via regex in code |

## Local Development

```
graph-theory-toolkit/
├── backend/     # FastAPI + graph core + algorithms + tests + benchmarks
├── frontend/    # Vite + React visualizer
├── docs/        # Algorithm write-ups
└── README.md
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000  
- Health: `GET /health`  
- Tests: `pytest`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173  
- Defaults to `http://localhost:8000`. For a remote API, copy `frontend/.env.example` → `frontend/.env` and set `VITE_API_URL`.

## Documentation

| Doc | Topic |
|-----|--------|
| [00 — Overview](docs/00-overview.md) | Project goals, structure, methodology |
| [01 — Traversal & connectivity](docs/01-traversal.md) | BFS, DFS, topo sort, SCC, bridges, articulation points |

Further modules (`02`–`07`) are planned under [`docs/`](docs/).

## License

Educational / portfolio project. See repository for source.
