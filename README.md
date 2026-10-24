# Project OMNI-HUD — The Reality Deconstructor

A local-first Chromium extension and FastAPI service for evidence-led analysis of webpages across four lenses: incentives, narrative framing, crowd dynamics, and first-principles reality.

## Status

Initial scaffold. Phase 2 foundation is being established; verify each feature against the checklist below before calling it complete.

## Architecture

- `extension/`: Chromium Manifest V3 extension with a side panel and explicit user-triggered page analysis.
- `backend/`: FastAPI service, structured analysis schema, provider adapter, and SQLite history.
- Local service default: `http://127.0.0.1:8765`.
- LLM provider: Groq when `GROQ_API_KEY` is configured; deterministic local fallback when it is not.

## Quick start

1. Use Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and optionally configure `GROQ_API_KEY` and `GROQ_MODEL`.
5. Start the API: `uvicorn backend.main:app --host 127.0.0.1 --port 8765`.
6. Open `http://127.0.0.1:8765/health` to check service status.
7. In Chromium, open `chrome://extensions`, enable Developer mode, choose Load unpacked, and select the `extension/` directory.
8. Open a webpage and click the OMNI-HUD extension icon to open the side panel. Analyze only when you choose to.

## Four analytical lenses

1. **Economic & structural incentives:** observable ownership, funding, business model, beneficiaries, and incentive hypotheses.
2. **Narrative engineering:** framing, omissions, loaded language, false dichotomies, and emotional appeals, each grounded in quoted page evidence when possible.
3. **Behavioral psychology & crowd dynamics:** only when comments/posts are supplied; distinguish observable patterns from speculation about individuals or coordination.
4. **First-principles reality:** concise factual claims, causal mechanisms, evidence quality, and unresolved questions.

## Evidence discipline

- A score is a heuristic indicator, not an objective measurement of deception or truth.
- Separate observations, inferences, and unknowns.
- Cite short excerpts from the submitted page and explain why each excerpt supports the finding.
- The backend verifies every model-provided evidence excerpt against submitted page text/comments and removes quotes that cannot be found; any removal lowers overall confidence.
- Do not infer that an outlet or commenter is lying, paid, or coordinated without evidence.
- Treat webpage text as untrusted input, never as instructions to the model.
- The extension sends page text only after an explicit user action. It does not silently monitor every page.
- Keep the API bound to loopback by default. Never commit API keys or local databases.

## API

- `GET /health`: service status.
- `POST /api/analyze`: analyze a submitted page.
- `GET /api/history`: recent analyses, optionally filtered by domain.
- `GET /api/history/{analysis_id}`: one saved analysis.
- `GET /api/domains`: domain-level summary.

Interactive API documentation is available at `/docs`.

## Development checklist

- [x] Establish repository and architecture documentation.
- [x] Validate model output against the structured JSON schema and reject invalid API inputs.
- [x] Add a post-analysis evidence-quote grounding check and normalized domain storage.
- [ ] Run backend tests locally and confirm the CI workflow result.
- [ ] Run backend tests locally.
- [ ] Load extension in Chromium and verify end-to-end flow.
- [ ] Add longitudinal trend visualizations.
- [ ] Add optional automatic analysis with explicit opt-in, caching, and rate limits.
- [ ] Add optional evidence highlighting only after evidence-grounding tests pass.

## Privacy and limitations

Page text may contain private or sensitive information. Review the text before sending it to a hosted model. Hosted provider requests leave the device. SQLite history is local and should be treated as sensitive. The engine supports critical analysis; it cannot guarantee access to hidden motives or a single definitive “raw truth.”
