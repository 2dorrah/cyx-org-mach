#!/usr/bin/env python3
"""
CYTHANX ORGANISM
================

A deterministic, executable "interloped" organism inspired by the supplied
CYTHANX poster.  This is a research/toy composition, not a cryptocurrency
miner and not a real quantum/AI system.

Pipeline:
    BLOCK HEADER
        -> ENIGMA-STYLE PERMUTATION
        -> DYNO-256 STATE
        -> JOATT IDENTITY
        -> CYTHANIZE VECTOR
        -> TRANSMOGRIFY
        -> AUXILIARY 128-BIT DIGEST
        -> ORGANISM / AI-LIKE ADAPTATION
        -> NETWORK STATE
        -> BOUNDED "IMPOSSIBLE" STATE

Requirements:
    Python 3.10+
    pip install blake3

Run:
    python cythanx_organism.py
    python cythanx_organism.py --seed CYTHANX --rounds 8 --json

No network connection is made. No real Bitcoin keys, payouts, or mining are
performed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import math
import struct
import time
from dataclasses import dataclass, asdict
from typing import Iterable

try:
    from blake3 import blake3
except ImportError as exc:
    raise SystemExit("Missing dependency: pip install blake3") from exc



# ---------------------------------------------------------------------------
# Primitive layers
# ---------------------------------------------------------------------------

def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def blake3_256(data: bytes) -> bytes:
    return blake3(data).digest(length=32)


def blake3_128(data: bytes) -> bytes:
    return blake3(data).digest(length=16)


def scrypt256(data: bytes, salt: bytes = b"CYTHANX-SCRYPT") -> bytes:
    return hashlib.scrypt(
        password=data,
        salt=salt,
        n=1024,
        r=1,
        p=1,
        dklen=32,
    )


def canonical(obj: object) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def pbkdf2_512(data: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha512", data, salt, 2048, dklen=64)


# ---------------------------------------------------------------------------
# Enigma-style permutation
# ---------------------------------------------------------------------------

ALPHABET = bytes(range(256))


def rotor_permute(data: bytes, rotor: int) -> bytes:
    out = bytearray(len(data))
    for i, value in enumerate(data):
        # Reversible byte-domain permutation with a position-dependent rotor.
        x = (value + rotor + i * 17) & 0xFF
        x ^= ((rotor * 29 + i * 7) & 0xFF)
        out[i] = ((x << 3) | (x >> 5)) & 0xFF
    return bytes(out)


def reflector(data: bytes) -> bytes:
    return bytes((255 - x) for x in data)


def enigma(data: bytes) -> bytes:
    x = rotor_permute(data, 11)
    x = rotor_permute(x, 37)
    x = rotor_permute(x, 73)
    x = reflector(x)
    x = rotor_permute(x, 73)
    x = rotor_permute(x, 37)
    return rotor_permute(x, 11)


# ---------------------------------------------------------------------------
# JOATT identity/state layer
# ---------------------------------------------------------------------------

def joatt_state(data: bytes, previous: bytes = b"") -> dict:
    root = blake3_256(data + previous)
    tree = sha256d(root + data)
    stretched = pbkdf2_512(tree, b"CYTHANX|JOATT|2048")
    memory = scrypt256(stretched[:32], b"CYTHANX|MEMORY")
    mix = blake3_256(root + tree + memory)

    identifier64 = mix[:8]
    checksum = hashlib.adler32(mix) & 0xFFFFFFFF

    return {
        "root": root.hex(),
        "sha256d": tree.hex(),
        "memory": memory.hex(),
        "state256": mix.hex(),
        "identifier64": identifier64.hex(),
        "adler32": f"{checksum:08x}",
    }


# ---------------------------------------------------------------------------
# CYTHANIZE + TRANSMOGRIFY
# ---------------------------------------------------------------------------

def cythanize(data: bytes, domain: bytes = b"VECTOR") -> dict:
    vector = blake3_256(b"CYTHANX|" + domain + b"|" + data)
    digest = sha256d(vector)
    work = scrypt256(digest, b"CYTHANX|VECTOR|SCRYPT")
    commitment = blake3_256(vector + digest + work)

    return {
        "vector": vector.hex(),
        "sha256d": digest.hex(),
        "scrypt": work.hex(),
        "commitment": commitment.hex(),
    }


def transmogrify(data: bytes, rounds: int = 3) -> bytes:
    x = data
    for i in range(rounds):
        x = enigma(x)
        x = blake3_256(
            b"CYTHANX|TRANSMOGRIFY|" + bytes([i & 0xFF]) + x
        )
        x = scrypt256(x, f"round-{i}".encode())
    return x


# ---------------------------------------------------------------------------
# 128-bit auxiliary layer
# ---------------------------------------------------------------------------

def aes128_aux(data: bytes) -> bytes:
    """
    Dependency-free 128-bit auxiliary layer.

    The original poster calls this layer 128-bit auxiliary. Since the requested build
    removes the cryptography package, this implementation deliberately uses
    a BLAKE3-128 domain-separated digest instead of claiming to perform AES.
    """
    key = hashlib.sha256(b"CYTHANX|AUX|V1").digest()[:16]
    return blake3_128(b"CYTHANX|AUX128|" + key + data)


# ---------------------------------------------------------------------------
# DYNO-256 adaptive state
# ---------------------------------------------------------------------------

@dataclass
class DynoState:
    state: bytes
    difficulty: float = 1.0
    generation: int = 0

    def evolve(self, signal: bytes) -> None:
        material = (
            b"CYTHANX|DYNO256|"
            + self.state
            + signal
            + struct.pack(">Q", self.generation)
        )
        self.state = blake3_256(material)
        # Bounded adaptive value; this is not a proof-of-work target.
        sample = int.from_bytes(self.state[:4], "big") / 0xFFFFFFFF
        self.difficulty = 1.0 + 15.0 * sample
        self.generation += 1


# ---------------------------------------------------------------------------
# Organism / bounded AI-like adaptation
# ---------------------------------------------------------------------------

@dataclass
class Organism:
    energy: float = 1.0
    entropy: float = 0.0
    health: float = 1.0
    generation: int = 0

    def perceive(self, payload: bytes) -> float:
        digest = blake3_256(payload)
        x = int.from_bytes(digest[:8], "big") / 2**64
        self.entropy = -math.log2(max(x, 2**-64)) / 64.0
        return x

    def adapt(self, signal: bytes) -> None:
        x = self.perceive(signal)

        # Bounded adaptation: no self-modifying code and no external I/O.
        learning = 0.02 + 0.08 * x
        self.energy = max(0.0, min(2.0, self.energy * (0.98 + learning)))
        self.health = max(
            0.0, min(1.0, 0.97 * self.health + 0.03 * (1.0 - abs(x - 0.5)))
        )
        self.generation += 1


# ---------------------------------------------------------------------------
# Network-state simulation
# ---------------------------------------------------------------------------

def network_state(payload: bytes, peers: int = 8) -> dict:
    digest = blake3_256(b"CYTHANX|NETWORK|" + payload)
    score = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF

    return {
        "peers": peers,
        "connectivity": round(score, 8),
        "protocol": "CYTHANX/ORGANISM-1",
        "state_hash": digest.hex(),
    }


# ---------------------------------------------------------------------------
# Bounded "impossible algorithm"
# ---------------------------------------------------------------------------

def impossible_state(
    header: bytes,
    joatt: dict,
    cyx: dict,
    dyno: DynoState,
    organism: Organism,
) -> dict:
    """
    The poster calls this an "impossible algorithm." Here it is implemented as
    a finite deterministic composition, so it remains executable and testable.
    """
    seed = (
        header
        + bytes.fromhex(joatt["state256"])
        + bytes.fromhex(cyx["commitment"])
        + dyno.state
        + struct.pack(">Q", organism.generation)
    )

    layers = []
    state = seed

    for i in range(8):
        state = blake3_256(
            b"CYTHANX|IMPOSSIBLE|"
            + bytes([i])
            + state
            + sha256d(state)
        )
        layers.append(state.hex())

    return {
        "layers": layers,
        "final_state": state.hex(),
        "finite": True,
        "iterations": 8,
    }


# ---------------------------------------------------------------------------
# Interloper: ties every algorithmic organ together
# ---------------------------------------------------------------------------

def interlope(seed: bytes, rounds: int) -> dict:
    header = (
        b"CYTHANX-HEADER"
        + struct.pack(">I", 1)
        + blake3_256(seed)
        + sha256d(seed)
        + struct.pack(">I", int(time.time()))
        + b"\x00" * 8
    )[:80].ljust(80, b"\0")

    dyno = DynoState(blake3_256(b"CYTHANX|GENESIS|" + seed))
    organism = Organism()

    previous_joatt = b""
    history = []

    for round_no in range(rounds):
        stage0 = enigma(header + dyno.state)

        joatt = joatt_state(stage0, previous_joatt)
        vector = cythanize(
            bytes.fromhex(joatt["state256"]),
            b"ORGANISM"
        )

        transformed = transmogrify(
            bytes.fromhex(vector["commitment"]),
            rounds=3 + (round_no % 3),
        )

        aux = aes128_aux(transformed)
        dyno.evolve(aux)
        organism.adapt(aux)

        net = network_state(aux)

        impossible = impossible_state(
            header,
            joatt,
            vector,
            dyno,
            organism,
        )

        previous_joatt = bytes.fromhex(joatt["state256"])

        history.append({
            "round": round_no,
            "joatt_id": joatt["identifier64"],
            "dyno_difficulty": round(dyno.difficulty, 8),
            "organism_energy": round(organism.energy, 8),
            "organism_health": round(organism.health, 8),
            "network_connectivity": net["connectivity"],
            "final_state": impossible["final_state"],
        })

        # Feed the evolved organism back into the next header state.
        header = blake3_256(
            header
            + dyno.state
            + bytes.fromhex(impossible["final_state"])
        )

    return {
        "name": "CYTHANX ORGANISM",
        "seed": seed.decode("utf-8", errors="replace"),
        "rounds": rounds,
        "final_dyno_state": dyno.state.hex(),
        "organism": asdict(organism),
        "history": history,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the bounded CYTHANX organism pipeline."
    )
    parser.add_argument("--seed", default="CYTHANX")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.rounds <= 1000:
        raise SystemExit("--rounds must be between 1 and 1000")

    result = interlope(args.seed.encode(), args.rounds)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("╔════════════════════════════════════════════╗")
    print("║          CYTHANX ORGANISM                 ║")
    print("║     INTERLOPED ALGORITHM ENGINE            ║")
    print("╚════════════════════════════════════════════╝")
    print(f"Seed:       {result['seed']}")
    print(f"Rounds:     {result['rounds']}")
    print(f"Generation: {result['organism']['generation']}")
    print(f"Energy:     {result['organism']['energy']:.8f}")
    print(f"Health:     {result['organism']['health']:.8f}")
    print(f"Entropy:    {result['organism']['entropy']:.8f}")
    print(f"DYNO state: {result['final_dyno_state']}")
    print("\nEvolution:")
    for item in result["history"]:
        print(
            f"  [{item['round']:03d}] "
            f"JOATT={item['joatt_id']} "
            f"DYNO={item['dyno_difficulty']:.5f} "
            f"ENERGY={item['organism_energy']:.5f} "
            f"HEALTH={item['organism_health']:.5f}"
        )


if __name__ == "__main__":
    main()
