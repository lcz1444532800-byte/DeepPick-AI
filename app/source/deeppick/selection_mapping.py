from difflib import SequenceMatcher
import math


def remap_selection(previous, following):
    """Keep the user's chosen spans when AI corrects the text in an existing line."""
    selected = previous.indices
    output = set()
    used = set()
    for old, old_offset in zip(previous.blocks, previous.offsets):
        local = {index - old_offset for index in selected if old_offset <= index < old_offset + len(old.text)}
        if not local:
            continue
        candidates = [(index, block) for index, block in enumerate(following.blocks) if index not in used
                      and abs(block.x-old.x) < max(12, old.height)
                      and abs(block.y-old.y) < max(12, old.height)]
        if not candidates:
            continue
        index, new = min(candidates, key=lambda pair: abs(pair[1].x-old.x) + abs(pair[1].y-old.y))
        used.add(index)
        offset = following.offsets[index]
        for tag, a, b, c, d in SequenceMatcher(None, old.text, new.text, autojunk=False).get_opcodes():
            if tag == 'equal':
                output.update(offset + c + position - a for position in local if a <= position < b)
            elif tag == 'replace':
                for position in local:
                    if a <= position < b:
                        start = c + math.floor((position-a)*(d-c)/max(1,b-a))
                        end = c + math.ceil((position-a+1)*(d-c)/max(1,b-a))
                        output.update(range(offset+start, offset+end))
            elif tag == 'insert' and a > 0 and a-1 in local and a in local:
                output.update(range(offset+c, offset+d))
    return output
