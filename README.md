# Graph Theory Toolkit

Graph Theory Toolkit is an educational and research-oriented monorepo for exploring classic graph algorithms — including traversal, shortest paths, minimum spanning trees, network flows, and centrality measures — with complexity analysis and validation against real-world datasets.

## Project structure

```
graph-theory-toolkit/
├── backend/          # FastAPI API + graph core + algorithms
├── frontend/         # Vite + React visualization UI
├── docs/             # Documentation
└── README.md
```

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Health check: `GET /health`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173` and talks to the backend on port 8000.
