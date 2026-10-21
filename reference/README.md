# Recorded protocol evidence

The direct observation session took place on 2026-10-21 against the authorized Old Calculator endpoint on port 4873.

- [PROTOCOL.md](PROTOCOL.md): measured behavior and remaining unknowns.
- [summary.json](summary.json): session counts and 16 recovered functions.
- [compatibility_cases.json](compatibility_cases.json): consolidated observed requests and responses.
- [wire.jsonl](wire.jsonl), [followup_wire.jsonl](followup_wire.jsonl), [closing_wire.jsonl](closing_wire.jsonl): socket reads and writes with UTC timestamps, text, and hex.

`recv` chunk boundaries depend on TCP delivery. The hex fields retain the actual observed bytes. The complete contents of every original array and the original random generator were unavailable.

The original successful solve's final round is recorded separately in [examples/round16.json](../examples/round16.json). The local recorded scenario comes from this later direct observation session.
