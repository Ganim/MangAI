# Workers Service

This service runs asynchronous MangAI jobs.

Current bootstrap:

- worker settings and CLI entrypoint
- deterministic `detect_regions` stub runner
- state-backed queue processor for local jobs
- handler registry and dispatch function
- automated tests for config, queue processing, and job execution
