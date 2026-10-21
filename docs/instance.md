# Old Calculator — local Docker instance

Securinets · author: [kristoferUA](https://github.com/kristoferUA)

[English](instance.md) · [Українська](instance.uk.md)

Linux Docker service implementing the observed Old Calculator protocol on port **4873**. It includes the four arithmetic operations, fractional arithmetic, the selected-value reading, 16 rounds, measured error responses, and a configurable flag. A local copy of the successful solver is included.

[Back to the writeup](../README.md)

## Start and retrieve the flag

Requirements: Docker Engine. The quick start uses its Compose plugin; Docker Engine commands are also provided below. The client can run inside the same image, so the host does not need Python.

Clone the repository and run the following commands. With an extracted bundle, start from its existing folder:

```bash
git clone https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup.git Securinets-old-calculator
cd Securinets-old-calculator
cp .env.example .env
docker compose up -d --build --wait
```

The service is available at `127.0.0.1:4873`:

```bash
nc 127.0.0.1 4873
```

Run the complete 16-round solution inside the container:

```bash
docker compose exec -T --workdir /tmp calculator \
  python /app/solve.py --run --host 127.0.0.1 \
  --trace /tmp/local_trace.jsonl
```

The final line starts with `FLAG: Securinets{...}`. The client first opens a separate connection to check exact fractional reading, then starts its solving session.

Save the trace on the host:

```bash
docker compose exec -T calculator cat /tmp/local_trace.jsonl > local_trace.jsonl
```

Use the stdout command above for files in the container's `/tmp` mount. The trace is temporary and is lost when the container is recreated.

## Use a prebuilt Linux image

The complete bundle includes `release-assets/old-calculator-linux-amd64.tar.gz`. From the repository root:

```bash
docker load -i release-assets/old-calculator-linux-amd64.tar.gz
docker compose up -d --no-build --wait
```

The GitHub source archive contains the repository files. For a source-only checkout, obtain the image from the published GitHub Release when available and place it under `release-assets/`. Publication instructions are in [publishing.md](publishing.md).

Loading the image allows deployment without downloading the base image. On another CPU architecture, build from the Dockerfile.

## Run with Docker Engine

These commands deploy the same image using Docker Engine directly:

```bash
cp .env.example .env
docker run -d --name old-calculator-local --restart unless-stopped \
  -p 127.0.0.1:4873:4873 --env-file .env \
  --read-only --tmpfs /tmp:rw,mode=1777 --init \
  --cap-drop ALL --security-opt no-new-privileges:true \
  old-calculator-local:latest
docker exec -w /tmp old-calculator-local \
  python /app/solve.py --run --host 127.0.0.1 --trace /tmp/local_trace.jsonl
```

Load the prebuilt image first, or build it with `docker build -t old-calculator-local:latest .`. With `docker run`, edit the `-p` argument directly to change the host port. To apply environment changes, recreate this project container:

```bash
docker rm -f old-calculator-local
```

Then run the deployment command again. Its transient trace can be saved with `docker exec old-calculator-local cat /tmp/local_trace.jsonl > local_trace.jsonl`.

## Replay the recorded session

This mode uses the 16 functions, test arguments, and original input entries `0` and `99` observed on 2026-10-21:

```bash
docker compose -f compose.yaml -f compose.recorded.yaml up -d --wait
docker compose exec -T --workdir /tmp calculator \
  python /app/solve.py --run --host 127.0.0.1 \
  --sample-indices 0 99 --trace /tmp/recorded_trace.jsonl
```

With these indices, the packed selected values and test arguments reproduce the observed 16-round dialogue. The other 98 original array entries were unavailable and are filled with deterministic local values satisfying the same function.

Return to the default random mode:

```bash
docker compose up -d --wait
```

This assumes `CALCULATOR_MODE=random` in `.env`.

## Configuration

Edit `.env`, then apply changes with `docker compose up -d --force-recreate --wait`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Host interface on which Docker publishes the port |
| `HOST_PORT` | `4873` | Host TCP port; the container continues using `4873` |
| `CALCULATOR_MODE` | `random` | `random` or `recorded` |
| `CALCULATOR_SEED` | empty | Optional seed string for repeatable local data |
| `FLAG` | Original Old Calculator flag | Flag returned after 16 correct answers |

Use the usual `Securinets{your_value}` shape for a custom flag when using the included solver. The service returns the configured string.

Random mode chooses `a,b` uniformly from `1..16` and input/test values from `0..255`, using Python's `SystemRandom`. Setting a seed uses `random.Random(seed)` independently for each new connection; the same interaction then gives the same round data. The original generator and distributions were not established by the available evidence.

With a fixed seed, an ambiguous pair can recur after reconnecting. Change the seed or use another pair with `--sample-indices FIRST SECOND`. Entry `98` is the solver's scratch cell.

## Run the client on the host

With Python 3.12:

```bash
python3 solve.py --run --host 127.0.0.1 --port 4873 --trace local_trace.jsonl
```

The local copy defaults to `127.0.0.1`. Compared with the original solver, it adds `--host`, `--port`, and `--sample-indices`; the 42-bit packing and coefficient recovery are preserved.

The original remote solver is archived at [solvers/solve_remote_original.py](../solvers/solve_remote_original.py).

## Access a Linux host over SSH

Open a tunnel from the client computer to the Linux host running the service:

```bash
ssh -N -L 14873:127.0.0.1:4873 user@linux-host
```

Keep that connection open, then use the client computer's forwarded port:

```bash
python3 solve.py --run --host 127.0.0.1 --port 14873 --trace forwarded_trace.jsonl
```

## Service operations

```bash
docker compose ps
docker compose logs --tail 50 calculator
docker compose restart calculator
docker compose down
```

For a different host port, set `HOST_PORT=14873` in `.env`; the in-container solver command remains unchanged.

The image uses the official [Python image](https://hub.docker.com/_/python), runs as UID/GID `10001`, and includes a greeting health check. Compose's [health-check support](https://docs.docker.com/compose/how-tos/startup-order/) is used by the documented startup workflow.

## Protocol fidelity

The service reproduces the observed prompt bytes, arithmetic, selected-value formatting, error wrappers, and round/connection transitions. This includes acceptance of `0.5`, rejection of negative displayed values, the distinct `255.5` display error, numeric-answer equality, and closure after errors or the final flag.

Implementation choices for previously unmeasured behavior:

- All 100 entries are recreated at each round; the live study directly tracked entries `0` and `99`.
- Unmeasured JSON types and incomplete lines at stream EOF follow Python's JSON, indexing, and line-reading behavior.
- Measured validation precedence is preserved; other combinations follow the order in `server.py`.
- No application-level operation or idle timer is added.
- Random generation follows the explicitly selected local mode.

The full evidence is in [reference/PROTOCOL.md](../reference/PROTOCOL.md). The recorded scenario is [fixtures/recorded_session.json](../fixtures/recorded_session.json).

## Files

```text
server.py                    TCP service
solve.py                     local copy of the working solver
healthcheck.py               checks the initial greeting
Dockerfile                   Linux image, Python 3.12
compose.yaml                 default local deployment
compose.recorded.yaml        recorded-session override
.env.example                 port, mode, seed, and flag settings
fixtures/recorded_session.json
reference/                   live protocol evidence
examples/                    local completion records
LICENSE                      MIT, kristoferUA
```
