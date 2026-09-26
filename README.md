# ChangeStory

ChangeStory is a local, deterministic developer tool for answering a practical review question: *what changed, what might be affected, why, and what should be checked next?* It is deliberately Python-only for its first version. It does not use an LLM, modify source code, execute uploaded code, or claim complete runtime dependency analysis.

## How it works

```text
unified Git diff
     │
     ├─ parse changed files and line ranges
     ├─ map added Python lines to built-in AST symbols
     ├─ find conservative, direct static callers
     ├─ attach source/diff evidence
     ├─ apply deterministic risk and test rules
     └─ store an exportable local report
                 │
                 ├─ Next.js dashboard
                 └─ CLI summary / report URL
```

The dashboard deliberately separates detected facts, potential risks, suggested tests, and actual controlled execution results.

## Repository layout

```text
app/                 Next.js 16 dashboard and report route
backend/app/         FastAPI API, diff parser, AST engine, reports, runner
backend/tests/       Unit, integration, and runner-boundary tests
cli/                 Installable `changestory analyze` command
sample-project/      Only repository that the verification runner can execute
fixtures/diffs/      Three deterministic demo diffs
reports/             Generated JSON/Markdown reports (ignored by Git)
```

## Requirements

- Node.js 20.9+ (tested with Node 20.20)
- Python 3.11+ (tested with Python 3.14)
- No API key, database, account, or cloud service

## Install and run

Install the backend and CLI once:

```powershell
cd backend
python -m pip install -e ".[dev]"
cd ..\cli
python -m pip install -e .
```

Start the two local services in separate terminals:

```powershell
# terminal 1, from repository root
cd backend
python -m uvicorn app.main:app --reload --port 8000

# terminal 2, from repository root
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Select one of the three demo scenarios or paste a unified Git diff. The browser always analyzes against `sample-project`.

## CLI

With the API running, analyze current Git changes or a diff file:

```powershell
changestory analyze --repo C:\path\to\your\python-repo
changestory analyze --repo . --diff-file fixtures\diffs\calculation.diff --no-browser
```

The CLI sends analysis input to the local API and opens the frontend report URL. It does not duplicate analysis logic.

## Demo scenarios

1. **Calculation change** — `calculate_total` changes; direct callers, a focused test reference, and shared-impact evidence are displayed.
2. **API handler change** — `get_price_summary` changes; the report suggests an integration-level check.
3. **Shared utility change** — `normalize_label` changes; consumers in catalog and notifications show broader impact.

## API

- `GET /health`
- `POST /api/v1/analyze` with `{ "diff_text": "...", "source_mode": "sample" }`
- `GET /api/v1/reports/{session_id}`
- `GET /api/v1/reports/{session_id}/export.json`
- `GET /api/v1/reports/{session_id}/export.md`
- `POST /api/v1/reports/{session_id}/verify`

Next.js serves the user-facing report at `/report/{session_id}`.

## Tests and checks

```powershell
cd backend
python -m pytest -q

cd ..
npm run lint
npm run build
```

The backend tests cover unified-diff parsing, AST/change mapping, caller evidence, report exports, API health, and the fact that verification accepts no user-provided command. The dashboard uses its real FastAPI response at runtime and is checked by TypeScript/ESLint and a production build.

## Security model

Analysis can read a local Python source tree for the CLI workflow, but execution is intentionally much narrower: verification uses one hard-coded `python -m pytest -q` argument list, `shell=False`, a 30-second timeout, and the bundled `sample-project` working directory. The frontend exposes neither command nor path controls for verification. Reports use opaque hash-derived IDs and no secrets are stored.

## Intentional limitations

- Python syntax and conservative static direct calls only; dynamic imports, reflection, dispatch, and runtime dependencies are not resolved.
- Test matching is a static reference heuristic, not coverage proof.
- Browser demos are tied to the bundled controlled sample project.
- A potential risk is a review signal, never a confirmed defect.

Python-only keeps the proof of concept dependable, inspectable, and easy to extend without pretending every language has the same analysis guarantees.

## Troubleshooting

- **Dashboard says service unavailable:** start FastAPI on port 8000, or set `NEXT_PUBLIC_CHANGESTORY_API` before starting Next.js.
- **CLI cannot connect:** verify `http://127.0.0.1:8000/health` and use `--api-url` if your port differs.
- **No symbols map:** ensure changed paths in the diff match Python paths in the selected repository and changed lines are present in the current source.
- **CLI is not on PATH on Windows:** use `python -m changestory_cli.main analyze ...` from `cli/`, or add your user Python Scripts directory to PATH.

## Hackathon evidence

`bob_sessions/` is an empty placeholder. Screenshots and evidence must be captured by the human team during a real demo; ChangeStory does not fabricate Bob sessions, screenshots, source evidence, or test outcomes.
