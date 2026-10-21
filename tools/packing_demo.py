#!/usr/bin/env python3
"""Reproduce the recorded Old Calculator final round locally.

Author: kristoferUA. Standard library only; this helper opens no connection.
"""

import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = importlib.util.spec_from_file_location("old_calculator_solver", ROOT / "solve.py")
    solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solver)
    case = json.loads((ROOT / "examples" / "round16.json").read_text(encoding="utf-8"))
    (x0, y0), (x1, y1) = case["samples"]
    word = ((x0 * 8192 + y0) * 256 + x1) * 8192 + y1
    reading = math.ldexp(word, -35)
    points, decoded_word = solver.decode_value(repr(reading))
    possible = solver.candidates(points)
    if decoded_word != case["packed_word"] or len(possible) != 1:
        raise RuntimeError("recorded example did not reconstruct uniquely")
    a, b = possible[0]
    answer = a * case["test_input"] + b
    if repr(reading) != case["selected_value_text"] or answer != case["client_answer"]["y"]:
        raise RuntimeError("recorded reading or answer did not match")
    print("round: %d" % case["round"])
    print("packed word: %d" % word)
    print("selected value: %r" % reading)
    print("decoded samples: %r" % points)
    print("a: %d" % a)
    print("b: %d" % b)
    print("f(%d): %d" % (case["test_input"], answer))
    print("recorded final-round calculation matches")


if __name__ == "__main__":
    main()
