# Workers Service

This service runs asynchronous MangAI jobs.

Current bootstrap:

- worker settings and CLI entrypoint
- asset-aware heuristic `detect_regions` adapter
- state-backed queue processor for local jobs
- handler registry and dispatch function
- automated tests for config, queue processing, and job execution
