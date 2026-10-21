#!/usr/bin/env python3
"""Check the local service's full greeting without submitting an answer."""

import os
import socket


def main():
    expected = b"Round 1:\nEnter JSON: "
    with socket.create_connection(("127.0.0.1", int(os.getenv("PORT", "4873"))), timeout=2) as connection:
        connection.settimeout(2)
        data = b""
        while len(data) < len(expected):
            chunk = connection.recv(len(expected) - len(data))
            if not chunk:
                return 1
            data += chunk
        return 0 if data == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
