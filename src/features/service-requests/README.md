# Service requests

This module owns the request lifecycle used by users and staff: API calls, request queue and review workflows, and conversion between editable forms and report or calendar payloads.

User-facing pages live in `src/views` and compose this module. Keep route handling and presentation in those views; keep request contracts and lifecycle rules here. Legacy booking and course compatibility remains outside this module.
