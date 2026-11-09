# Contributing

The workflow matches the FQE project kickoff: one branch per task, a pull request for every change, and a passing CI run before merge.

1. Pick an item from [docs/ROADMAP.md](docs/ROADMAP.md) and tell the project lead.
2. Branch from `main`: `git switch -c <phase>/<short-task>`, for example `p2/exact-bond-repricing`.
3. Keep game logic in `packages/engine` as pure functions with no I/O, so the server, the simulation harness, and the prep-kit sandbox all share one implementation.
4. Add a test for every formula. Where the design spec has a worked example, use its numbers as the test case.
5. Run `pnpm typecheck && pnpm test` and `pnpm test:data` before you push.
6. Open a pull request. One review and a green CI run are required to merge.

## Conventions

- TypeScript in strict mode; no `any`.
- Python in `data/` uses the standard library only, so the pipeline runs anywhere without installs.
- Units go in names or doc comments: yields are decimals in the engine, basis points where named `*Bp`, money in U.S. dollars.
- Briefing and debrief text is written by people. Do not commit generated narration.
- Do not commit built episode data or anything from a licensed source until the licensing check in [data/README.md](data/README.md) is done.
