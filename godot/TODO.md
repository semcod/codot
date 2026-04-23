# Godot Roadmap / TODO

## Phase 1 - core stability
- [x] Align bundle schema with Go structs and support application bundles
- [x] Keep existing bundle examples valid under the schema
- [x] Stabilize `make start` and service readiness checks

## Phase 2 - LLM and ACL
- [ ] Finalize LiteLLM prompts for service, view, workflow, and application bundles
- [ ] Extend ACL rules for local network / internet access control
- [ ] Keep on-demand endpoint fetching available for the LLM service

## Phase 3 - testing and generated artifacts
- [ ] Add more NLP prompt fixtures for bundle generation
- [ ] Make generated bundles automatically visible in recursive validation
- [ ] Add integration tests for Go deployment paths when bundle runners are wired in fully

## Phase 4 - platform expansion
- [ ] Add desktop / mobile / web / PWA generation templates
- [ ] Connect generated bundles to real runtime deployers
- [ ] Document schema generation and bundle lifecycle end-to-end
