# Changelog

## V0.1.0 - 12-13-2025

### Added
- Scaffolded the Telegram bot structure with command handlers, scheduler placeholder, and Google Sheets client skeleton. (#1)
- Documented the Phase 1 implementation approach and hosting assumptions. (#2)
- Added Telegram interaction handlers and wiring for the Command agent. (#3)
- Implemented the Command & Journal agent with parsing utilities and comprehensive tests. (#4)
- Implemented the Google Sheets storage agent with integration helpers and tests. (#5)
- Added configurable reminder scheduling with environment-driven defaults and tests. (#6)

### Changed
- Strengthened configuration validation, environment handling, and credential loading. (#7)
- Expanded logging configuration, instrumentation, and validation across the bot and storage layers. (#8)
- Extended parsing, command, and Google Sheets client test coverage; refreshed contributor guidance. (#9)
- Documented runtime execution, container usage, and operational guidance in README and Dockerfile. (#10)
