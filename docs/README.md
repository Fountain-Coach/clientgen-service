# FountainAI Client Generator Service — Redesign Plan and Intent

## Current Context

The Client Generator service was initially designed to asynchronously generate Python SDK clients from OpenAPI specifications, supporting concurrency and webhook notifications. However, in practical use:

- The client is exclusively called by a single LLM agent.
- The existing concurrency and background job processing model introduces complexity and unreliability.
- End-to-end and async tests hang or fail unpredictably.
- The route prefix handling caused confusion and duplicated segments, complicating integration and testing.
- Directory access and SDK persistence need to be publicly accessible, adding operational constraints.
- The service architecture is not fully testable and maintainable as is.

## Core Goals of the Client Generator

- Accept OpenAPI specs from the LLM-driven planner.
- Generate and persist Python SDK clients based on those specs.
- Provide job status updates and completion notifications.
- Keep job management simple and reliable, with predictable lifecycle transitions.
- Integrate smoothly into the FountainAI ecosystem with clear API contracts.

## Key Realizations

- Since the clientgen service is called by one LLM agent at a time, concurrency is not a critical requirement.
- The job lifecycle can be simplified into a mostly synchronous or serialized async flow to avoid race conditions and hanging.
- Webhooks and job state notifications should be made more straightforward or deferred if unnecessary.
- The OpenAPI spec must remain the single source of truth for API endpoints and models.
- Testing must be aligned with simplified service behavior, focusing on robustness and reliability.

## Proposed Redesign Strategy

1. **Simplify Job Management**
   - Move away from concurrent job queues to a serialized job process.
   - Remove background worker loops in favor of direct async task execution or synchronous processing.
   - Ensure immediate job status availability without indefinite hanging.

2. **Refactor API Endpoints**
   - Clean up router prefixes; avoid duplicate segments.
   - Align route paths strictly with OpenAPI spec.
   - Remove unnecessary complexity in webhooks or postpone advanced webhook functionality.

3. **Improve Directory and Persistence Handling**
   - Ensure SDK output directories exist and are writable on startup.
   - Make generated SDK directories accessible through Caddy proxy (or relevant proxy).
   - Document and test directory permissions and access explicitly.

4. **Revise Testing Approach**
   - Build focused async test suites using proper async HTTP client integration.
   - Add serial integration smoke tests simulating LLM calls and job status queries.
   - Remove flaky or hanging tests by adjusting service logic or test timeouts.

5. **Documentation and Developer Experience**
   - Maintain the OpenAPI spec as the source of truth.
   - Keep main service entrypoint minimal; configure routers with clean prefixes.
   - Provide detailed README and usage instructions highlighting the simplified architecture.

## Next Steps

- Finalize a minimal working version of the clientgen service following the above principles.
- Implement and pass focused async tests.
- Deploy and verify correct SDK generation and persistence behavior.
- Iterate on webhook and notification features post-stabilization.
- Monitor integration with LLM planner to confirm expected usage pattern.

