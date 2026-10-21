# Old Calculator: earlier protocol notes

Historical notes retained from the initial writeup. The subsequent direct study is documented in [reference/PROTOCOL.md](../reference/PROTOCOL.md), and the local service is described in [instance.md](instance.md).

Author: [kristoferUA](https://github.com/kristoferUA) · Competition: Securinets

This reference describes the Old Calculator service on the recorded port `4873`, specifically the updated prompt used by the successful solver. It is a basis for a future compatible local implementation. Server source code and a complete raw capture of the successful connection were not available.

The other calculator services on ports `4874` and `4875` have different behavior and are outside this specification.

## Evidence levels

- **Observed:** directly shown in supplied responses or the successful-session screenshot.
- **Validated model:** an arithmetic assumption used by the successful 16-round solver and checked locally.
- **Unresolved:** behavior that must be specified or measured before claiming complete server compatibility.

The fixtures in `examples/` record visible fields and numerical results. They are not packet captures. In particular, the templates do not establish every trailing space, newline, JSON separator, or TCP segmentation choice.

## Session states

```text
connect
  -> Round 1 / Enter JSON
  -> zero or more arithmetic requests
  -> submit selected entry
  -> selected value and fresh test input
  -> client sends {"y": result}
       correct, rounds 1..15 -> next round / Enter JSON
       correct, round 16    -> flag
       incorrect            -> error and connection closes
```

An actual failed answer was followed by `recv()` returning empty bytes. Reconnecting begins a new session at round 1.

The successful client sends one request at a time and waits for the next protocol event. Support for multiple complete requests in one received buffer is not established by this specification.

## Arrays and arithmetic

| Property | Status | Details |
| --- | --- | --- |
| Array names | Observed | `x` and `y` |
| Array length | Provided interface | 100 entries each |
| Source index 100 | Observed | Rejected with `Invalid index` |
| Destination index 100 | Observed | Rejected with `Invalid index` |
| Initial relation | Validated model | `y[i] = a*x[i] + b` |
| Initial input bounds | Validated model | `0 <= x[i] <= 255` |
| Coefficient bounds | Validated model | `1 <= a,b <= 16` |
| Intermediate values | Observed and validated | Not reduced modulo 256 |
| Negative arithmetic | Observed | `const=-1` is accepted |
| Fractional arithmetic | Observed | `const=0.5` is accepted |
| Display precision | Observed and validated | The 42-bit fraction used by the solver can be recovered exactly |

The model does not prescribe the exact random-number generator or distributions. The successful solver recomputes the coefficients every round.

## Request objects

Binary arithmetic:

```json
{"operation":"add","source":["x","y"],"source_index1":0,"source_index2":1,"destination":"x","dest_index":98}
{"operation":"mult","source":["x","y"],"source_index1":0,"source_index2":1,"destination":"y","dest_index":98}
```

Constant arithmetic:

```json
{"operation":"add_const","source":"x","index":0,"const":1,"destination":"x","dest_index":98}
{"operation":"mult_const","source":"x","index":0,"const":0.5,"destination":"x","dest_index":98}
```

Reading the selected value and entering the final question:

```json
{"operation":"submit","source":"x","index":98}
```

Answering the final question:

```json
{"y":3422}
```

The answer is the hidden function applied to the supplied test input. It is independent of how the displayed entry was computed.

## Successful arithmetic response

The visible result object is:

```json
{"result": "Operation successful"}
```

It is followed by `Enter JSON:`. The working client identifies this prompt without assuming that one socket read contains the full response.

## Updated final-question template

```text
the value of x[98] you submitted is: <selected_value>
As a final Test please give the value after applying the secret operation of the random number <t>:
{"y" : number }
```

The last successful round used:

```text
selected_value = 30.055107453401433
t = 228
a = 15
b = 2
client answer = {"y":3422}
```

The final flag object was:

```json
{"flag":"Securinets{ed9a482110a5a6936482e700155f811742f97a04decfa75d3cee28bca77239c1}"}
```

JSON whitespace in this illustration is normalized. The flag content and final-round numerical values are transcribed from the successful run.

## Earlier final-question format

Before the prompt update, supplied dialogues showed:

```text
As a final Test, please submit the value of the result of the operation of this number with the value at the index you submitted, which is:  <t>
{"y" : number }
```

That number must not be interpreted as a reading of the selected entry. In separate observations, entries explicitly set to `0` and `7` were followed by displayed numbers `151` and `108`, respectively. The later format resolves this ambiguity by printing the selected entry and the test input separately.

This is a historical protocol variant. The packaged solver targets the updated format above. A future local service needs an explicit choice of which variant it reproduces.

## Errors shown during solving

These messages were observed. Their visible content is useful for compatibility, but their presence does not establish the order in which every invalid request is checked.

| Situation | Visible message |
| --- | --- |
| Source or destination array name is invalid | `Array must be x or y` |
| Source or destination index is invalid | `Invalid index` |
| Constant `65536` was supplied | `Constant must be 8-bit` |
| Unsupported operation | `Unsupported operation` |
| Missing field such as `source` | Key-error text such as `'source'` |
| Large displayed integer | `Value at y[99] is 11 bits, which cannot be represented as 8-bit:` |
| Negative displayed value | `Value at x[98] is negative, which cannot shown for performance reasons:` |
| Wrong final answer | `Incorrect value submitted. Expected 57, but got 3048` |

Some validation errors are direct JSON error objects. Display and final-answer errors were also shown with an outer `error` field containing another JSON object encoded as a string. A compatible representation of that observed shape is:

```python
inner = {"error": "Incorrect value submitted. Expected 57, but got 3048"}
outer = {"error": json.dumps(inner)}
```

This code illustrates the response shape; it is not quoted server source. Machine-readable object examples are in [responses.json](../examples/responses.json).

## Remaining compatibility decisions

The following details are unresolved by the available evidence:

- The exact generator, seeding, distribution, and lifecycle of coefficients, inputs, and test arguments.
- The full original values of all 100 entries in any live round.
- Exact whitespace and newline placement for every response variant.
- Transport framing when requests are combined in a single TCP write.
- Validation order when a request has more than one invalid field.
- Handling of negative indices, booleans, non-finite numbers, numeric strings, and unusual JSON types.
- Any operation count or session-duration limits.
- The exact numeric predicate used for the displayed-value size restriction.
- Normal successful display wording for all source/index combinations beyond the captured `x[98]` case.
- Whether every class of error closes the connection. Closure after a wrong final answer is confirmed.

A future local service can reproduce the confirmed dialogue and arithmetic model, with deterministic fixtures for the recorded final round. Exact agreement for the unresolved cases requires an explicit behavior choice or additional evidence.
