# Old Calculator — live protocol specification

Securinets · author: [kristoferUA](https://github.com/kristoferUA) · observed 2026-10-21

Endpoint: `calculator-crypto.securinets.tn:4873`. Observed IPv4: `158.158.74.206`.

This document extends the earlier evidence-based protocol notes with direct observations. The study completed 16 rounds, recorded 47 observation connections and one greeting-only connection, and confirmed the final flag. This specification is the input for a subsequent local service implementation.

The supporting files contain socket bytes and parsed observations. Server source, the original random generator, and its state were unavailable.

## 1. Evidence files

| File | Contents |
| --- | --- |
| [compatibility_cases.json](compatibility_cases.json) | Consolidated requests, parsed responses, and outcomes |
| [summary.json](summary.json) | Counts and all 16 recovered round functions |
| [wire.jsonl](wire.jsonl) | Main study: UTC time, direction, raw hex, decoded text |
| [followup_wire.jsonl](followup_wire.jsonl) | Numeric boundaries, line framing, and answer types |
| [closing_wire.jsonl](closing_wire.jsonl) | Negative constant boundary, same-line JSON, binary multiplication |

Raw `send` and `recv` records preserve exact bytes. The additional `response` records are client parsing events. TCP read boundaries vary, so an emulator should reproduce the byte stream and application behavior rather than particular `recv` chunk sizes.

## 2. Transport and framing

The service uses a persistent TCP connection. Ordinary requests are one JSON object per newline-terminated line.

Confirmed behavior:

1. A complete object without `\n` produced no response during a five-second observation.
2. Sending a complete object, waiting 250 ms, then sending `\n` caused normal execution.
3. Splitting a request into two writes, with `\n` only at the end, caused normal execution.
4. Two distinct newline-terminated requests in one write were both executed in order. Starting from zero, `+7` then `*2` produced `14`.
5. Two adjacent JSON objects on one line caused a JSON `Extra data` error and EOF.
6. A blank line caused a JSON parse error and EOF.

The exact same-line parse error in the recorded example was:

```text
Extra data: line 1 column 94 (char 93)
```

The column depends on the serialized request length. The blank-line error was:

```text
Expecting value: line 1 column 1 (char 0)
```

The behavior of an unterminated final line followed by a TCP write-half-close was not measured.

## 3. Session states and exact output templates

### Connection greeting

The complete greeting was:

```python
b'Round 1:\nEnter JSON: '
```

The current Old Calculator instance does not include the introductory lines shown by the later calculator tasks.

### Arithmetic success

```python
b'{"result": "Operation successful"}\nEnter JSON: '
```

### Selected entry and final question

For a successful submission, the observed template is:

```python
(
    f'the value of {source}[{index}] you submitted is: {value}\n'
    f'As a final Test please give the value after applying the secret operation of the random number {t}: \n'
    '{"y" : number }'
).encode('utf-8')
```

Both `x[98]` and `y[97]` were directly read. The second line has a space after the colon, followed by a newline. The final `{"y" : number }` prompt has no terminating newline in the recorded dialogue.

### Correct answer, rounds 1–15

```python
f'Round {next_round}:\nEnter JSON: '.encode('utf-8')
```

This next-round prompt is the acceptance indication.

### Correct answer, round 16

The exact observed final response was:

```python
b'{"flag": "Securinets{ed9a482110a5a6936482e700155f811742f97a04decfa75d3cee28bca77239c1}"}\n'
```

The server then closed the connection; EOF was confirmed.

## 4. Arrays, arithmetic, and round state

The interface has arrays `x` and `y` with indices `0..99`. Index `99` is usable; both `-1` and `100` are rejected for source and destination.

The successful model for the initial values is:

```text
y[i] = a*x[i] + b
a,b in 1..16
x[i] in 0..255
```

These bounds are the validated solving model. The study does not establish the exact generator or probabilities over those domains.

The four arithmetic requests have these forms:

```json
{"operation":"add","source":["x","y"],"source_index1":0,"source_index2":1,"destination":"x","dest_index":98}
{"operation":"mult","source":["x","y"],"source_index1":96,"source_index2":97,"destination":"x","dest_index":98}
{"operation":"add_const","source":"x","index":0,"const":0.5,"destination":"y","dest_index":97}
{"operation":"mult_const","source":"x","index":0,"const":128,"destination":"x","dest_index":98}
```

Each line above is a separate request. Results overwrite the destination entry. Binary cross-array multiplication of known entries `7` and `9` yielded `63`.

Large intermediate values are stored without automatic reduction modulo 256. All 16 rounds used a 42-bit packed value followed by 35 multiplications by `0.5` to recover two exact pairs.

### Relationship between tables and the hidden function

In each round the client first packed the original pairs at indices `0` and `99`. It then set `x[99]=255`, `y[99]=0`, submitted the packed value from `x[98]`, and answered using the original function.

All 16 answers were accepted. Mutating a table pair therefore did not redefine the function used to grade that round.

At all 15 subsequent round transitions, the pair at index `99` had been replaced, and both decoded pairs matched the new recovered function. The entries at indices `0` and `99` support a fresh-array model. The study did not read all 100 entries before and after each transition.

## 5. Constants, indices, and validation

### Constants

Accepted examples include integers `-255`, `0`, `1`, `128`, `255` and floats `-0.5`, `0.0`, `0.5`, `254.5`, `255.0`.

Rejected examples:

| Input | Error text |
| --- | --- |
| `const=256` | `Constant must be 8-bit` |
| `const=-256` | `Constant must be 8-bit` |
| `const=255.5` | `Constant must be 8-bit` |
| `const="2"` | `'<=' not supported between instances of 'int' and 'str'` |

For finite ordinary numeric inputs, the compatible boundary rule is `-255 <= const <= 255`; fractional constants are supported on this port.

The exact string-constant error, without Markdown escaping, is:

```text
'<=' not supported between instances of 'int' and 'str'
```

### Indices and array names

| Input | Error text |
| --- | --- |
| Source index `-1` or `100` | `Invalid index` |
| Destination index `-1` or `100` | `Invalid index` |
| Source index `"0"` | `'<=' not supported between instances of 'int' and 'str'` |
| Source index `0.5` | `list indices must be integers or slices, not float` |
| Source array `"z"` | `Array must be x or y` |
| Destination array `"z"` | `Array must be x or y` |

### Missing fields and operation dispatch

Missing fields produced the corresponding quoted key text, for example `'operation'`, `'source'`, `'index'`, `'const'`, `'destination'`, `'dest_index'`.

`{"operation":"divide"}` produced `Unsupported operation` even without arithmetic fields.

### Confirmed relative validation priorities

The combined-invalid cases establish these priorities:

| Simultaneous problems | Observed error |
| --- | --- |
| Source `"z"`, source index `-1`, constant `256` | `Array must be x or y` |
| Source index `-1`, constant `256` | `Invalid index` |
| Destination `"z"`, constant `256` | `Array must be x or y` |

These establish partial precedence. They do not establish every validation order for every operation or missing-field combination.

## 6. Reading and numeric formatting

Reading a cell uses:

```json
{"operation":"submit","source":"x","index":98}
```

The following readings were directly observed:

| Stored value | Selected-value text or error |
| --- | --- |
| Integer `0` | `0` |
| Float `0.0` | `0.0` |
| Float `0.5` | `0.5` |
| Float `254.5` | `254.5` |
| Integer `255` | `255` |
| Float `255.0` | `255.0` |
| Float `1/2**25` | `2.9802322387695312e-08` |
| Integer `256` | `Value at x[98] is 9 bits, which cannot be represented as 8-bit:` |
| Float `255.5` | `'float' object cannot be interpreted as an integer` |
| Negative `-0.5` or `-255` | `Value at x[98] is negative, which cannot shown for performance reasons:` |

Python's ordinary integer/float string formatting reproduces the recorded accepted numeric texts. For the measured finite numeric domain, successful display is consistent with `0 <= value <= 255`.

The out-of-range float error is distinct from the out-of-range integer error and uses a different wrapper. A compatible implementation must preserve this distinction for the recorded cases.

## 7. Final-answer rules

After displaying the entry, the service supplies a separate random argument `t`. The answer is the original function value `a*t+b`, sent as a JSON object with key `y`.

```json
{"y":168}
```

The exactly equivalent numeric value `{"y":168.0}` was accepted in round 1 of the complete session. Correct integer answers were accepted in rounds 2–16.

In a separate session, the recovered correct value was `1302`. Sending `{"y":"1302"}` was rejected with:

```text
Incorrect value submitted. Expected 1302, but got 1302
```

Numeric strings are not automatically converted into accepted numeric answers. The message prints the string contents without quotation marks.

`{"a":0}` at the final question yielded `Missing 'y' in input`. Both this case and a deliberately incorrect numeric answer were followed by EOF.

## 8. Error serialization and connection closure

All 31 measured error cases ended in server EOF.

### Direct error object

Array/index/constant validation, missing arithmetic fields, JSON parsing, unsupported operations, and the out-of-range float reading used:

```python
(json.dumps({"error": message}) + '\n').encode('utf-8')
```

### Nested error object

Negative readings, oversized integer readings, missing final key `y`, and rejected final answers used:

```python
inner = json.dumps({"error": message})
wire = (json.dumps({"error": inner}) + '\n').encode('utf-8')
```

For example:

```json
{"error": "{\"error\": \"Missing 'y' in input\"}"}
```

These Python expressions reproduce the observed serialization shape and default JSON spacing. They describe compatible behavior; the server's actual implementation was not supplied.

## 9. Remaining limits on exact reproduction

The study resolves the normal solver workflow, measured numeric boundaries, ordinary error cases, line framing, selected-value formatting, next-round text, and terminal closure.

The following remain undetermined:

- The original random generator, seed source, generator state, and exact distributions.
- The complete initial contents of all entries in a particular live session.
- Any maximum operation count, numeric magnitude, session duration, or idle duration.
- Validation for unmeasured JSON values, including booleans, nulls, containers, non-finite numbers, and alternate binary-source shapes.
- Complete combined-error precedence and all malformed final-answer objects.
- Handling of an incomplete final line at TCP write-half-close.

A local implementation can match the confirmed dialogue and arithmetic behavior using scripted fixtures or a chosen random generator. Reproducing the original future random sequence requires information beyond the observed protocol.
