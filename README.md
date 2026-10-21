# Old Calculator

Securinets · crypto · author: [kristoferUA](https://github.com/kristoferUA)

[English](README.md) · [Українська](README.uk.md)

[Local instance](docs/instance.md) · [Observed protocol](reference/PROTOCOL.md) · [GitHub publication](docs/publishing.md)

**Docker service:** [Compose](compose.yaml) · [Dockerfile](Dockerfile) · [TCP server](server.py).

**Ready-to-run Linux amd64 image:** [Download — 45 MB](https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup/releases/download/v1.0.0/old-calculator-linux-amd64.tar.gz) · [SHA256](https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup/releases/download/v1.0.0/old-calculator-linux-amd64.tar.gz.sha256) · [Release v1.0.0](https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup/releases/tag/v1.0.0).

Old Calculator gives us arithmetic access to hidden input/output arrays and asks us to identify a function. The final solution packs two complete pairs into one exact binary fraction, reads that fraction through the calculator, and recovers the current function locally. It needs **45 arithmetic operations per round** and completed all **16 rounds**.

Flag:

```text
Securinets{ed9a482110a5a6936482e700155f811742f97a04decfa75d3cee28bca77239c1}
```

## Run the challenge locally

The repository includes the Linux Docker instance, its recorded-session mode, and a local solver. From the repository root:

```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T --workdir /tmp calculator \
  python /app/solve.py --run --host 127.0.0.1 --trace /tmp/local_trace.jsonl
```

Both random and recorded modes completed all 16 rounds. The recorded mode also reproduced all 16 selected-value questions from the direct observation session. Docker Engine commands, prebuilt-image loading, and configuration are in [the instance guide](docs/instance.md).

The root `solve.py` defaults to `127.0.0.1`. A byte-preserved copy of the original remote solver is in [solvers/solve_remote_original.py](solvers/solve_remote_original.py).

## Challenge interface

The recorded instance was:

```text
nc calculator-crypto.securinets.tn 4873
```

The service holds two arrays, `x` and `y`, with 100 entries each. Their initial values are hidden. We can add or multiply array entries, use constant variants of those operations, and write the result into a chosen destination entry.

These are the relevant request formats:

```json
{"operation":"add","source":["x","y"],"source_index1":0,"source_index2":1,"destination":"x","dest_index":98}
{"operation":"mult","source":["x","y"],"source_index1":0,"source_index2":1,"destination":"x","dest_index":98}
{"operation":"add_const","source":"x","index":0,"const":1,"destination":"x","dest_index":98}
{"operation":"mult_const","source":"x","index":0,"const":2,"destination":"x","dest_index":98}
{"operation":"submit","source":"x","index":98}
```

Each line above is a separate request. The client waits for the next prompt before sending another operation. A successful arithmetic request returns:

```text
{"result": "Operation successful"}
Enter JSON:
```

`submit` displays one selected entry and starts the final question for the current round. After a correct answer, the service advances to the next round. Sixteen correct answers produce the flag.

## What the observations established

There was no server source in the supplied challenge material. The solution was developed from the interaction notes and observed responses.

The successful model was:

$$
y_i=f(x_i)=ax_i+b,
\qquad a,b\in\{1,\ldots,16\},
\qquad x_i\in\{0,\ldots,255\}.
$$

Every round needs fresh coefficient recovery. A function that worked in one round did not necessarily work in the next.

The arithmetic and display behavior mattered just as much as the formula:

- Intermediate values are not automatically reduced modulo 256.
- Large integers and negative values are rejected when submitted for display.
- This version accepts the constant `0.5` and displays small fractional values.
- The successful, updated prompt shows the selected entry and a separate random test input.

The prompt used by the working solver is:

```text
the value of x[98] you submitted is: <selected value>
As a final Test please give the value after applying the secret operation of the random number <t>:
{"y" : number }
```

The selected value contains our encoded information. The final answer is `f(t)`, using the independent number `t` from the next line. Treating these as the same number gives the wrong answer.

This writeup targets that updated prompt. Earlier messages in the solving session used a less explicit format; the included solver expects the selected-value line.

## How the approach developed

The early attempts helped separate the hidden function from the arithmetic interface:

| Attempt | Observation | Consequence |
| --- | --- | --- |
| Write zero, then submit the entry | The final answer could still be nonzero | Changing a table entry does not redefine the hidden function |
| Construct a coefficient code assuming byte arithmetic | The result did not recover the expected coefficients | Writes must not be modeled as reduction modulo 256 |
| Submit a large intermediate integer | The service reports its bit length and rejects the reading | Storage and display have different limits |
| Submit a negative difference | The service rejects negative displayed values | A readable construction needs a suitable nonnegative value |
| Scale a packed integer with `0.5` | A small fraction retains the required information | Exact binary fractions provide the final reading method |

The prompt change was also decisive: it made the selected entry and the random test input explicit. Earlier guesses had sometimes treated the random input as a reading of the selected entry. The final method uses the selected entry to recover the function, then evaluates that function at the separate test input.

## Why two pairs are enough

For two distinct inputs, an affine function satisfies:

$$
a=\frac{y_1-y_0}{x_1-x_0},
\qquad b=y_0-ax_0.
$$

Once two pairs are available locally, recovering `a,b` is easy. The difficulty is reading both hidden pairs through a single accepted submission.

The useful observation is that a small fractional value can hold all of their significant bits. The display's magnitude restriction does not restrict a fraction to eight bits of information.

## Pack the pairs into 42 bits

We use the original pairs at indices `0` and `1`, leaving them unchanged during the calculation.

Each input fits in 8 bits. An output satisfies:

$$
0\le y_i\le16\cdot255+16=4096<2^{13}.
$$

Thirteen bits are sufficient for each output. Twelve would be insufficient for the boundary value `4096`.

The four fields therefore occupy 42 bits:

```text
| x0: 8 bits | y0: 13 bits | x1: 8 bits | y1: 13 bits |
```

Build the integer:

$$
M=\bigl((x_0\,2^{13}+y_0)\,2^8+x_1\bigr)\,2^{13}+y_1.
$$

By construction:

$$
0\le M<2^{42}.
$$

The calculator can store this large intermediate integer. We only need to transform it before submitting it.

The large factors are built from small accepted constants:

```text
8192 = 128 * 64
256  = 128 * 2
```

The first ten operations are equivalent to:

```python
scratch = x[0] * 1
scratch *= 128
scratch *= 64
scratch += y[0]
scratch *= 128
scratch *= 2
scratch += x[1]
scratch *= 128
scratch *= 64
scratch += y[1]
```

The actual client translates these lines into the documented JSON requests and stores the scratch value in `x[98]`.

## Make the packed value small without losing bits

Multiply the packed value by `0.5` exactly 35 times:

$$
v=\frac{M}{2^{35}}.
$$

Its range is now:

$$
0\le v<\frac{2^{42}}{2^{35}}=128.
$$

This small magnitude is accepted by the display. The calculation also preserves all the packed information:

1. Binary64 has 53 bits of significand precision; `M` uses at most 42.
2. Dividing by a power of two changes the binary exponent without discarding significant bits in this range.
3. None of the values approaches underflow.

The decimal response must preserve the binary value when parsed again. The successful server output did, and the client checks this before attempting the actual rounds.

The final operation count is:

```text
10 operations to pack two pairs
35 multiplications by 0.5
--------------------------------
45 arithmetic operations per round
```

## Check the reading precision first

The solver begins with a separate checking connection. It builds the maximum possible 42-bit word:

$$
M_{\max}=2^{42}-1=4398046511103.
$$

After scaling, the expected printed value is:

```text
127.9999999999709
```

Decoding must recover the original word and the artificial fields `(255,8191),(255,8191)`. This checks all 42 packed bits, including bits not exercised by a typical small sample.

The check then closes its connection at the final question. Writing known table entries does not set the server's hidden function, so this observation is not a coefficient-answering round.

## Recover the packed fields

Parse the response and undo the exponent shift:

```python
scaled = math.ldexp(float(selected_value), 35)
```

The implementation requires `scaled` to be integral and smaller than `2**42`. It then unpacks the fields from the least significant end:

```python
import math

def unpack(selected_value):
    value = float(selected_value)
    if not math.isfinite(value) or not 0 <= value < 128:
        raise ValueError("invalid selected value")

    scaled = math.ldexp(value, 35)
    if not scaled.is_integer():
        raise ValueError("the printed fraction lost required precision")
    word = int(scaled)
    if not 0 <= word < 2**42:
        raise ValueError("unexpected packed width")

    y1 = word & 8191
    word >>= 13
    x1 = word & 255
    word >>= 8
    y0 = word & 8191
    word >>= 13
    x0 = word & 255
    return [(x0, y0), (x1, y1)]
```

## Recover the current function

For distinct inputs, the slope formula determines `a,b`. The supplied solver additionally uses their small allowed ranges to handle all decoded cases uniformly:

```python
def coefficients(points):
    x0, y0 = points[0]
    possible = []
    for a in range(1, 17):
        b = y0 - a*x0
        if 1 <= b <= 16 and all(a*x+b == y for x, y in points):
            possible.append((a, b))
    return possible
```

Exactly one pair must remain. If the two input values coincide, the coefficient bounds can sometimes still determine a unique answer. Otherwise, the client closes the ambiguous session and starts a fresh solving connection within its configured retry limit.

An empty candidate set indicates that the decoded values do not match the assumed model; the solver reports that inconsistency.

## Answer all 16 rounds

For each round:

1. Construct the packed fraction in `x[98]` with 45 arithmetic requests.
2. Submit `x[98]` and parse the displayed fraction and fresh test input `t`.
3. Decode the two pairs and recover the unique `a,b`.
4. Send `{"y": a*t+b}`.
5. Wait for the next round prompt or the final flag.

The response reader keeps a persistent byte buffer. It searches for complete prompts and preserves any unread suffix, because TCP responses may arrive in fragments or together in the same read.

## Final round of the original solve

The recorded final round displayed:

```text
selected value = 30.055107453401433
test input     = 228
```

The exact reconstruction is:

$$
M=1032685628721,
$$

```text
(x0,y0) = (60,902)
(x1,y1) = (225,3377)
```

Therefore:

$$
a=\frac{3377-902}{225-60}=\frac{2475}{165}=15,
$$

$$
b=902-15\cdot60=2,
\qquad f(228)=15\cdot228+2=3422.
$$

The final client answer was:

```json
{"y":3422}
```

The server returned the flag shown at the top of this writeup. The numerical record is included in [examples/round16.json](examples/round16.json), with an annotated excerpt in [examples/success.txt](examples/success.txt).

## Running the solver and offline example

Python 3.12 is used by the Docker image. The solver and helper use only the standard library.

The solver's built-in local arithmetic check is available as:

```bash
python3 solve.py --self-check
```

It covers 2,048 affine cases, exact binary reconstruction, and the expected prompt fields. The original final-round calculation can be reproduced without a connection:

```bash
python3 tools/packing_demo.py
```

To use a running local instance from the host:

```bash
python3 solve.py --run --host 127.0.0.1 --port 4873 --trace local_trace.jsonl
```

To target the recorded competition endpoint explicitly:

```bash
python3 solve.py --run --host calculator-crypto.securinets.tn --port 4873 --trace remote_trace.jsonl
```

`--trace` requires a filename. The client records requests and responses as JSON Lines. It defaults to 16 rounds, with up to three solving connections if the pairs are ambiguous. Use `--sample-indices 0 99` with the recorded local scenario.

The fixture in `fixtures/recorded_session.json` comes from a separate direct study on 2026-10-21; its coefficients and selected values differ from the original solve above. The local replay follows that later recorded session.

## Repository layout

```text
Securinets-old-calculator/
  README.md / README.uk.md       full writeup in English and Ukrainian
  solve.py                      local solver with host/port options
  server.py / healthcheck.py     reconstructed TCP instance
  Dockerfile / compose.yaml      Linux deployment from this root
  compose.recorded.yaml          recorded-session mode
  .env.example                  port, mode, seed, flag
  solvers/solve_remote_original.py
  tools/packing_demo.py          offline original-round calculation
  fixtures/recorded_session.json
  reference/                    protocol and captured evidence
  examples/                     original result and local completion logs
  docs/instance.md / instance.uk.md
  docs/protocol-history.md       earlier observation notes
  docs/publishing.md             repository and release instructions
  release-assets/               prebuilt image in the complete bundle
  SHA256SUMS.txt / LICENSE       source checksums and MIT license
```

The GitHub source ZIP contains the repository files. The complete ZIP also contains the Linux image and its checksum under `release-assets/`. The image is prepared for a GitHub Release; Git tracks the source and documentation.

## Notes

The method depends on the arithmetic and serialization behavior of this Old Calculator version: exact binary scaling, acceptance of `0.5`, and enough printed precision to reconstruct the float. The initial hidden pairs must also fit the documented packing widths.

The [live protocol reference](reference/PROTOCOL.md) separates measured behavior from unresolved details. The local service reproduces the recorded dialogue and arithmetic; the original random generator and distributions remain unknown. Its explicit implementation choices are described in [the instance guide](docs/instance.md).
