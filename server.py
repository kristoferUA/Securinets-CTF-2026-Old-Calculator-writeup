#!/usr/bin/env python3
"""Old Calculator's observed TCP protocol, reconstructed for local practice.

Securinets / kristoferUA. See reference/PROTOCOL.md for observed behavior and
README.md for choices made where the original implementation was unavailable.
"""

import argparse
import json
import os
import random
import signal
import socket
import socketserver
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROUNDS = 16
ARRAY_SIZE = 100
DEFAULT_FLAG = "Securinets{ed9a482110a5a6936482e700155f811742f97a04decfa75d3cee28bca77239c1}"
SUCCESS = b'{"result": "Operation successful"}\nEnter JSON: '
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "recorded_session.json"


class DisplayError(ValueError):
    """The measured display failures use an additional JSON error wrapper."""


@dataclass(frozen=True)
class Config:
    host: str = "0.0.0.0"
    port: int = 4873
    flag: str = DEFAULT_FLAG
    mode: str = "random"
    seed: str | None = None


@dataclass(frozen=True)
class Selection:
    source: str
    index: Any
    value: Any


class CalculatorRound:
    def __init__(self, rng, recorded=None):
        self.rng = rng
        self.recorded = recorded
        self.a = recorded["a"] if recorded else rng.randint(1, 16)
        self.b = recorded["b"] if recorded else rng.randint(1, 16)
        x = [rng.randrange(256) for _ in range(ARRAY_SIZE)]
        if recorded:
            for index, value in recorded["x_overrides"].items():
                x[int(index)] = value
        self.tables = {"x": x, "y": [self.a * value + self.b for value in x]}

    def array(self, name):
        if name not in ("x", "y"):
            raise ValueError("Array must be x or y")
        return self.tables[name]

    @staticmethod
    def index(index):
        # Preserve native Python comparison/indexing errors for measured inputs.
        if not 0 <= index < ARRAY_SIZE:
            raise ValueError("Invalid index")
        return index

    def select(self, request):
        source, index = request["source"], request["index"]
        table = self.array(source)
        value = table[self.index(index)]
        if value < 0:
            raise DisplayError(
                f"Value at {source}[{index}] is negative, which cannot shown for performance reasons:")
        if value > 255:
            # bin(float) deliberately preserves the distinct observed TypeError.
            bits = len(bin(value)[2:])
            raise DisplayError(
                f"Value at {source}[{index}] is {bits} bits, which cannot be represented as 8-bit:")
        return Selection(source, index, value)

    def execute(self, request):
        operation = request["operation"]
        if operation == "submit":
            return self.select(request)
        if operation in ("add_const", "mult_const"):
            source = request["source"]
            index = request["index"]
            const = request["const"]
            destination = request["destination"]
            dest_index = request["dest_index"]
            source_table = self.array(source)
            destination_table = self.array(destination)
            self.index(index)
            self.index(dest_index)
            if not -255 <= const <= 255:
                raise ValueError("Constant must be 8-bit")
            left, right = source_table[index], const
        elif operation in ("add", "mult"):
            source1, source2 = request["source"]
            index1 = request["source_index1"]
            index2 = request["source_index2"]
            destination = request["destination"]
            dest_index = request["dest_index"]
            source_table1 = self.array(source1)
            source_table2 = self.array(source2)
            destination_table = self.array(destination)
            self.index(index1)
            self.index(index2)
            self.index(dest_index)
            left, right = source_table1[index1], source_table2[index2]
        else:
            raise ValueError("Unsupported operation")
        value = left + right if operation in ("add", "add_const") else left * right
        destination_table[dest_index] = value
        return None

    def test_input(self):
        return self.recorded["test_input"] if self.recorded else self.rng.randrange(256)


class CalculatorHandler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def write(self, data):
        self.wfile.write(data)

    def error(self, error, nested=False):
        message = str(error)
        if nested:
            message = json.dumps({"error": message})
        self.write((json.dumps({"error": message}) + "\n").encode("utf-8"))

    def handle(self):
        config = self.server.config
        if config.seed is not None:
            rng = random.Random(config.seed)
        elif config.mode == "recorded":
            rng = random.Random("old-calculator-recorded-fillers-v1")
        else:
            rng = random.SystemRandom()
        try:
            for number in range(1, ROUNDS + 1):
                recorded = self.server.recorded[number - 1] if self.server.recorded else None
                current = CalculatorRound(rng, recorded)
                self.write(f"Round {number}:\nEnter JSON: ".encode())
                while True:
                    line = self.rfile.readline()
                    if not line:
                        return
                    try:
                        selection = current.execute(json.loads(line))
                    except DisplayError as exc:
                        self.error(exc, nested=True)
                        return
                    except Exception as exc:
                        self.error(exc)
                        return
                    if selection is not None:
                        break
                    self.write(SUCCESS)
                t = current.test_input()
                self.write((
                    f"the value of {selection.source}[{selection.index}] you submitted is: {selection.value}\n"
                    f"As a final Test please give the value after applying the secret operation of the random number {t}: \n"
                    '{"y" : number }'
                ).encode("utf-8"))
                answer_line = self.rfile.readline()
                if not answer_line:
                    return
                try:
                    answer = json.loads(answer_line)
                    if "y" not in answer:
                        raise ValueError("Missing 'y' in input")
                    expected = current.a * t + current.b
                    if answer["y"] != expected:
                        raise ValueError(
                            f"Incorrect value submitted. Expected {expected}, but got {answer['y']}")
                except Exception as exc:
                    self.error(exc, nested=True)
                    return
            self.write((json.dumps({"flag": config.flag}) + "\n").encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Clients can close at any prompt, as the original solver's
            # preliminary fractional-reading connection does.
            return


class CalculatorServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, config):
        self.config = config
        self.recorded = None
        if config.mode == "recorded":
            self.recorded = json.loads(FIXTURE.read_text(encoding="utf-8"))["rounds"]
            if len(self.recorded) != ROUNDS:
                raise ValueError("Recorded fixture must contain 16 rounds")
            for entry in self.recorded:
                if not 1 <= entry["a"] <= 16 or not 1 <= entry["b"] <= 16:
                    raise ValueError("Recorded coefficients must be in 1..16")
                if not 0 <= entry["test_input"] <= 255:
                    raise ValueError("Recorded test inputs must be in 0..255")
                for index, value in entry["x_overrides"].items():
                    if not 0 <= int(index) < ARRAY_SIZE or not 0 <= value <= 255:
                        raise ValueError("Invalid recorded array entry")
        super().__init__((config.host, config.port), CalculatorHandler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("LISTEN_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "4873")))
    parser.add_argument("--mode", choices=("random", "recorded"),
                        default=os.getenv("CALCULATOR_MODE", "random"))
    parser.add_argument("--seed", default=os.getenv("CALCULATOR_SEED") or None)
    args = parser.parse_args()
    if args.mode not in ("random", "recorded"):
        parser.error("mode must be random or recorded")
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    config = Config(args.host, args.port, os.getenv("FLAG") or DEFAULT_FLAG,
                    args.mode, args.seed)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        with CalculatorServer(config) as server:
            host, port = server.server_address
            print(f"Old Calculator listening on {host}:{port}; mode={config.mode}; rounds=16", flush=True)
            server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
