"""Document representation used by the Batch A threshold calibration."""
import math

from .embed import embed


def unit(values):
    norm = math.sqrt(sum(x * x for x in values))
    if not norm:
        raise ValueError("Cannot normalize an empty or zero embedding")
    return [x / norm for x in values]


def document_vector(pieces, settings):
    texts = [f"{piece.section}\n{piece.text}" for piece in pieces]
    rows = [unit(row) for row in embed(texts, settings, stage="verification")]
    return unit([sum(column) / len(rows) for column in zip(*rows, strict=True)])


def version_key(version):
    parts = str(version).split("-")
    return tuple(map(int, parts)) if all(p.isdigit() for p in parts) else ()
