# Original remote solver

`solve_remote_original.py` is a byte-preserved copy of the solver used for the original Old Calculator instance. Its default endpoint is `calculator-crypto.securinets.tn:4873`.

```bash
python3 solvers/solve_remote_original.py --run --trace original_remote_trace.jsonl
```

For the local Docker instance, use the repository's root `solve.py`, which defaults to `127.0.0.1` and accepts host, port, and sample-index options.

Original SHA256: `ad558a0e991ba6ee83e7ba8f7d687e999df227eb9338953c059a3ee5d46480b7`.
