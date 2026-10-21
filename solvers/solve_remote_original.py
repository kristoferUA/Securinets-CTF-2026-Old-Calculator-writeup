#!/usr/bin/env python3
"""Read two affine samples through one exact binary fraction, then solve 16 rounds.

Only --run connects. One preliminary connection checks a known 42-bit value;
up to three solving connections are permitted if a sampled pair is ambiguous.
Uses the documented arithmetic, const=-1, and the confirmed const=0.5.
Only Python's standard library is required.
"""

import argparse
import json
import math
import re
import socket
import time


HOST = "calculator-crypto.securinets.tn"
PORT = 4873
VERSION = "1.0"
DEST = 98
SHIFT = 35
Y_BITS = 13
Y_BASE = 1 << Y_BITS
WORD_BITS = 42
READY = b"Enter JSON:"
FINAL = re.compile(rb'\{\s*"y"\s*:\s*number\s*\}')
ERROR = re.compile(rb'"error"\s*:')
VALUE = re.compile(
    rb"value\s+of\s+x\[98\]\s+you\s+submitted\s+is\s*:\s*"
    rb"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)", re.I)
TEST = re.compile(rb"random\s+number\s*(?::\s*)?(-?\d+)", re.I)
EXPECTED = re.compile(rb"Expected\s+(-?\d+)", re.I)
FLAG = re.compile(rb"[A-Za-z][A-Za-z0-9_]{1,48}\{[^{}\r\n]{1,512}\}")


class ProtocolError(RuntimeError):
    pass


class AmbiguousSamples(RuntimeError):
    pass


class Rejected(RuntimeError):
    pass


def unary(operation, source, const, destination=DEST):
    array, index = source
    return {"operation": operation, "source": array, "index": index,
            "const": const, "destination": "x", "dest_index": destination}


def binary(operation, left, right, destination=DEST):
    return {"operation": operation, "source": [left[0], right[0]],
            "source_index1": left[1], "source_index2": right[1],
            "destination": "x", "dest_index": destination}


def packing_commands(points):
    """Pack [8-bit x, 13-bit y, 8-bit x, 13-bit y], then halve 35 times."""
    (x0, y0), (x1, y1) = points
    target = ("x", DEST)
    commands = [
        unary("mult_const", x0, 1),
        unary("mult_const", target, 128),
        unary("mult_const", target, 64),
        binary("add", target, y0),
        unary("mult_const", target, 128),
        unary("mult_const", target, 2),
        binary("add", target, x1),
        unary("mult_const", target, 128),
        unary("mult_const", target, 64),
        binary("add", target, y1),
    ]
    commands.extend(unary("mult_const", target, 0.5) for _ in range(SHIFT))
    return commands


def decode_value(text):
    value = float(text)
    if not math.isfinite(value) or not 0 <= value < 128:
        raise ProtocolError("packed value must be finite and between 0 and 128")
    scaled = math.ldexp(value, SHIFT)
    if not scaled.is_integer():
        raise ProtocolError("printed fraction lost required binary digits")
    word = int(scaled)
    if not 0 <= word < (1 << WORD_BITS):
        raise ProtocolError("decoded value exceeds the 42-bit packing")
    rest = word
    y1 = rest & (Y_BASE - 1)
    rest >>= Y_BITS
    x1 = rest & 255
    rest >>= 8
    y0 = rest & (Y_BASE - 1)
    rest >>= Y_BITS
    x0 = rest & 255
    return [(x0, y0), (x1, y1)], word


def candidates(points):
    x0, y0 = points[0]
    result = []
    for a in range(1, 17):
        b = y0 - a * x0
        if 1 <= b <= 16 and all(a * x + b == y for x, y in points):
            result.append((a, b))
    return result


class Connection:
    def __init__(self, sock, trace, label):
        self.sock = sock
        self.trace = trace
        self.label = label
        self.buffer = bytearray()

    def record(self, direction, **fields):
        self.trace.write(json.dumps({"connection": self.label,
                                     "direction": direction, **fields},
                                    ensure_ascii=False) + "\n")

    def send(self, request):
        self.record("client", value=request)
        self.sock.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode())

    def event(self):
        while True:
            data = bytes(self.buffer)
            events = []
            ready = data.find(READY)
            if ready >= 0:
                events.append((ready, ready + len(READY), "ready"))
            for expression, kind in ((FINAL, "final"), (FLAG, "flag")):
                found = expression.search(data)
                if found:
                    events.append((found.start(), found.end(), kind))
            error = ERROR.search(data)
            if error:
                end = data.find(b"\n", error.start())
                if end >= 0:
                    events.append((error.start(), end + 1, "error"))
            if events:
                _, end, kind = min(events)
                response = data[:end]
                del self.buffer[:end]
                self.record("server", event=kind,
                            text=response.decode("utf-8", errors="replace"))
                return kind, response
            if len(data) > 1_000_000:
                raise ProtocolError("response exceeded 1 MB")
            chunk = self.sock.recv(8192)
            if not chunk:
                self.buffer.clear()
                kind = "error" if ERROR.search(data) else "eof"
                self.record("server", event=kind,
                            text=data.decode("utf-8", errors="replace"))
                return kind, data
            self.buffer.extend(chunk)

    def execute(self, commands, stage):
        for number, command in enumerate(commands, 1):
            self.send(command)
            kind, response = self.event()
            if kind != "ready":
                show(response)
                raise Rejected("%s stopped at operation %d/%d (%s)" %
                               (stage, number, len(commands), command["operation"]))
            if number % 16 == 0 or number == len(commands):
                print("  %s: operations %d/%d" % (stage, number, len(commands)), flush=True)

    def submit(self):
        self.send({"operation": "submit", "source": "x", "index": DEST})
        kind, response = self.event()
        show(response)
        if kind != "final":
            raise Rejected("server did not return a final-test prompt")
        selected, random_input = VALUE.search(response), TEST.search(response)
        if not selected or not random_input:
            raise ProtocolError("new prompt must include selected-cell value and random number")
        return selected.group(1).decode("ascii"), int(random_input.group(1))


def show(response):
    print("SERVER: " + response.decode("utf-8", errors="replace"), flush=True)


def open_connection(address, timeout, trace, label):
    sock = socket.create_connection((address, PORT), timeout=timeout)
    sock.settimeout(timeout)
    conn = Connection(sock, trace, label)
    try:
        kind, response = conn.event()
        show(response)
        if kind != "ready":
            raise ProtocolError("initial input prompt missing")
    except BaseException:
        sock.close()
        raise
    return sock, conn


def preflight(address, timeout, trace):
    print("\nSERVER CHECK: exact fractional reading of all 42 packed bits.", flush=True)
    sock, conn = open_connection(address, timeout, trace, "fraction-check")
    with sock:
        # Make exact 0, 255, and 8191 using accepted small integer constants.
        commands = [
            unary("mult_const", ("x", 0), -1, 94),
            binary("add", ("x", 0), ("x", 94), 95),
            unary("add_const", ("x", 95), 255, 96),
            unary("add_const", ("x", 95), 255, 97),
            unary("mult_const", ("x", 97), 32, 97),
            unary("add_const", ("x", 97), 31, 97),
        ]
        points = [(('x', 96), ('x', 97))] * 2
        conn.execute(commands + packing_commands(points), "fraction-check")
        value, _ = conn.submit()
        samples, word = decode_value(value)
        if word != (1 << WORD_BITS) - 1 or samples != [(255, 8191)] * 2:
            raise ProtocolError("server did not preserve the known 42-bit fraction")
        print("SERVER CHECK PASSED: %s preserves all 42 bits." % value, flush=True)
        print("Closing the checking connection without a final-test answer.", flush=True)


def solve_attempt(address, timeout, trace, attempt, rounds):
    print("\nSOLVING CONNECTION %d" % attempt, flush=True)
    sock, conn = open_connection(address, timeout, trace, "solve-%d" % attempt)
    with sock:
        commands = packing_commands([(("x", 0), ("y", 0)),
                                     (("x", 1), ("y", 1))])
        for number in range(1, rounds + 1):
            print("Round %d/%d: packing two samples (%d operations)." %
                  (number, rounds, len(commands)), flush=True)
            conn.execute(commands, "round-%d" % number)
            value, t = conn.submit()
            samples, _ = decode_value(value)
            possible = candidates(samples)
            print("  decoded samples=%r; coefficient pairs=%r" % (samples, possible), flush=True)
            if not possible:
                raise ProtocolError("decoded samples do not fit a*x+b with a,b in 1..16; "
                                    "no final answer was sent for this round")
            if len(possible) != 1:
                raise AmbiguousSamples("the two samples do not determine one coefficient pair; "
                                       "no final answer was sent for this round")
            a, b = possible[0]
            answer = a * t + b
            print("  a=%d, b=%d, random input=%d; sending y=%d" %
                  (a, b, t, answer), flush=True)
            conn.send({"y": answer})
            kind, response = conn.event()
            show(response)
            if kind == "flag":
                print("FLAG: " + FLAG.search(response).group(0).decode(), flush=True)
                return 0
            if kind == "error":
                expected = EXPECTED.search(response)
                if expected:
                    print("Expected=%s; sent=%d; decoded a=%d, b=%d" %
                          (expected.group(1).decode(), answer, a, b), flush=True)
                raise Rejected("final answer rejected; stopping without another attempt")
            if kind != "ready":
                raise ProtocolError("no acceptance prompt or flag after the answer; "
                                    "complete server response is recorded in the trace")
            print("ACCEPTED: round %d/%d" % (number, rounds), flush=True)
        print("All configured rounds were accepted.", flush=True)
        if rounds == 16:
            kind, response = conn.event()
            show(response)
            if kind == "flag":
                print("FLAG: " + FLAG.search(response).group(0).decode(), flush=True)
                return 0
            raise ProtocolError("16 answers accepted but no recognized flag; inspect the trace")
        return 0


def run(args):
    print("Endpoint: %s:%d" % (HOST, PORT), flush=True)
    print("Trace: " + args.trace, flush=True)
    print("Model: y=a*x+b; a,b in 1..16; x in 0..255; y below 8192.", flush=True)
    print("One fractional-reading check, then at most %d solving connection(s)." %
          args.attempts, flush=True)
    print("Resolving IPv4 address...", flush=True)
    addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(
        HOST, PORT, family=socket.AF_INET, type=socket.SOCK_STREAM)))
    if not addresses:
        raise ProtocolError("No IPv4 address returned")
    address = addresses[0]
    print("IPv4: " + ", ".join(addresses), flush=True)
    with open(args.trace, "w", encoding="utf-8", buffering=1) as trace:
        preflight(address, args.timeout, trace)
        for attempt in range(1, args.attempts + 1):
            try:
                return solve_attempt(address, args.timeout, trace, attempt, args.rounds)
            except AmbiguousSamples as exc:
                print("AMBIGUOUS: " + str(exc), flush=True)
                if attempt == args.attempts:
                    raise
                print("Starting a fresh solving connection within the configured limit.", flush=True)
    return 2


def simulate(commands, x, y):
    tables = {"x": list(x), "y": list(y)}
    for command in commands:
        operation = command["operation"]
        if operation.endswith("_const"):
            left = tables[command["source"]][command["index"]]
            right = command["const"]
        else:
            left = tables[command["source"][0]][command["source_index1"]]
            right = tables[command["source"][1]][command["source_index2"]]
        if operation in ("add", "add_const"):
            result = left + right
        elif operation in ("mult", "mult_const"):
            result = left * right
        else:
            raise AssertionError("unexpected arithmetic operation")
        tables[command["destination"]][command["dest_index"]] = result
    return tables["x"][DEST]


def self_check():
    commands = packing_commands([(("x", 0), ("y", 0)),
                                 (("x", 1), ("y", 1))])
    cases = 0
    inputs = [(0, 255), (1, 254), (15, 16), (16, 15),
              (255, 0), (127, 128), (17, 17), (0, 0)]
    for a in range(1, 17):
        for b in range(1, 17):
            for x0, x1 in inputs:
                x, y = [0] * 100, [0] * 100
                x[0], x[1] = x0, x1
                y[0], y[1] = a * x0 + b, a * x1 + b
                packed = simulate(commands, x, y)
                samples, word = decode_value(repr(packed))
                if samples != [(x0, y[0]), (x1, y[1])]:
                    raise AssertionError("sample packing lost information")
                if (a, b) not in candidates(samples):
                    raise AssertionError("coefficient recovery lost the actual function")
                cases += 1
    for word in [0, 1, (1 << WORD_BITS) - 1] + [1 << bit for bit in range(WORD_BITS)]:
        _, recovered = decode_value(repr(math.ldexp(word, -SHIFT)))
        if recovered != word:
            raise AssertionError("binary fraction did not survive printed round trip")
    fixture = (b'the value of x[98] you submitted is: 1.0\n'
               b'As a final Test please give the value after applying the secret operation '
               b'of the random number 225: \n{"y" : number }')
    if VALUE.search(fixture).group(1) != b"1.0" or TEST.search(fixture).group(1) != b"225":
        raise AssertionError("observed server prompt could not be parsed")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--self-check", action="store_true")
    parser.add_argument("--rounds", type=int, default=16)
    parser.add_argument("--attempts", type=int, default=3,
                        help="restart only for ambiguous samples; maximum 3 (default 3)")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--trace")
    args = parser.parse_args()
    if not 1 <= args.rounds <= 16 or not 1 <= args.attempts <= 3 or args.timeout <= 0:
        parser.error("rounds must be 1..16, attempts 1..3, and timeout positive")
    print("OLD CALCULATOR fractional sample solver v" + VERSION, flush=True)
    cases = self_check()
    print("LOCAL CHECK: %d arithmetic cases, 42-bit precision, and observed prompt passed." %
          cases, flush=True)
    if args.self_check:
        print("Local checks complete; no network activity.", flush=True)
        return 0
    args.trace = args.trace or ("calculator_fraction_trace_%s.jsonl" %
                                time.strftime("%Y%m%d_%H%M%S"))
    try:
        return run(args)
    except (OSError, RuntimeError) as exc:
        print("STOP: %s: %s" % (type(exc).__name__, exc), flush=True)
        print("The trace contains every request and response.", flush=True)
        return 2
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
