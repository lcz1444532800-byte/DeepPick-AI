from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float
    polygon: tuple = ()
    source: str = "local"

    def to_dict(self):
        return {"text": self.text, "x": self.x, "y": self.y, "width": self.width,
                "height": self.height, "confidence": self.confidence,
                "polygon": self.polygon, "source": self.source}

    @classmethod
    def from_dict(cls, value, max_width, max_height):
        if not isinstance(value, dict) or not isinstance(value.get("text"), str):
            raise ValueError("Invalid text block format")
        text = value["text"][:10000]
        nums = [float(value[k]) for k in ("x", "y", "width", "height", "confidence")]
        if not all(math.isfinite(v) for v in nums):
            raise ValueError("Text coordinates must be finite")
        x, y, w, h, confidence = nums
        if not text or w <= 0 or h <= 0 or x < 0 or y < 0 or x >= max_width or y >= max_height:
            raise ValueError("Text coordinates exceed the capture")
        w, h = min(w, max_width-x), min(h, max_height-y)
        polygon = value.get("polygon", ())
        if polygon:
            if len(polygon) != 4 or any(len(p) != 2 for p in polygon):
                raise ValueError("Invalid text polygon")
            polygon = tuple(tuple(float(v) for v in p) for p in polygon)
            if any(not math.isfinite(v) for p in polygon for v in p):
                raise ValueError("Invalid text polygon")
            if any(px < 0 or py < 0 or px > max_width or py > max_height for px, py in polygon):
                polygon = ()
        return cls(text, x, y, w, h, min(1., max(0., confidence)), polygon,
                   value.get("source", "local"))


def reading_order(blocks):
    """Cluster by vertical overlap, then sort left to right within each row."""
    rows = []
    for block in sorted(blocks, key=lambda b: (b.y + b.height/2, b.x)):
        center = block.y + block.height/2
        row = next((r for r in reversed(rows)
                    if abs(center-r[0]) <= min(block.height, r[1]) * .55), None)
        if row is None:
            rows.append([center, block.height, [block]])
        else:
            row[2].append(block)
    return [b for row in rows for b in sorted(row[2], key=lambda b: b.x)]


def join_fragments(fragments):
    # fragments carry (text, Block, first_character_index).
    out = ""
    previous = None
    for text, block, start in fragments:
        if not text:
            continue
        if previous:
            prev, prev_start, prev_text = previous
            same_row = abs((block.y+block.height/2)-(prev.y+prev.height/2)) <= min(block.height, prev.height)*.55
            if block is prev:
                separator = " " if start > prev_start + len(prev_text) else ""
            elif same_row:
                # CJK neighbors need no artificial spaces; separate distant columns.
                gap = block.x - (prev.x + prev.width)
                latin = prev_text[-1:].isascii() and text[:1].isascii()
                separator = "\t" if gap > max(block.height, prev.height)*2 else (" " if latin or gap > block.height*.8 else "")
            else:
                gap = block.y - (prev.y+prev.height)
                separator = "\n\n" if gap > max(prev.height, block.height)*.8 else "\n"
            out += separator
        out += text
        previous = (block, start, text)
    return out.strip()


def all_text(blocks):
    return join_fragments([(b.text, b, 0) for b in reading_order(blocks)])


def should_enhance(settings, blocks):
    if settings.mode == "local" or not settings.auto_enhance or not settings.api_key:
        return False
    if settings.mode == "ai":
        return True
    if not blocks:
        return True
    count = sum(len(b.text) for b in blocks)
    average = sum(b.confidence*len(b.text) for b in blocks)/max(1, count)
    return average < settings.threshold or any(b.confidence < .55 for b in blocks)


class Selection:
    def __init__(self, blocks):
        self.blocks = reading_order(blocks)
        self.offsets = []
        self.length = 0
        for block in self.blocks:
            self.offsets.append(self.length)
            self.length += len(block.text)
        self.committed = set()
        self.preview = set()

    @property
    def indices(self):
        return self.committed | self.preview

    def range(self, first, last):
        self.preview = set(range(min(first, last), max(first, last)+1))

    def commit(self):
        self.committed |= self.preview
        self.preview.clear()

    def clear(self):
        self.committed.clear()
        self.preview.clear()

    def text(self):
        fragments = []
        chosen = self.indices
        for block, offset in zip(self.blocks, self.offsets):
            run = ""
            start = 0
            for i, char in enumerate(block.text):
                if offset+i in chosen:
                    if not run:
                        start = i
                    run += char
                elif run:
                    fragments.append((run, block, start))
                    run = ""
            if run:
                fragments.append((run, block, start))
        return join_fragments(fragments)
