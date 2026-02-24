from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RuleChunk:
    id: str
    text: str
    metadata: Dict[str, str]


def split_into_paragraphs(text: str) -> List[str]:
    blocks: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        else:
            current.append(stripped)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def chunk_rules(text: str, source: str, max_chars: int = 1500) -> List[RuleChunk]:
    paragraphs = split_into_paragraphs(text)
    chunks: List[RuleChunk] = []
    buffer: List[str] = []
    section_index = 0
    for para in paragraphs:
        candidate = ("\n\n".join(buffer + [para])).strip()
        if len(candidate) > max_chars and buffer:
            section_id = f"{source}-section-{section_index}"
            chunks.append(
                RuleChunk(
                    id=section_id,
                    text="\n\n".join(buffer).strip(),
                    metadata={"rule_id": section_id, "source": source, "section": str(section_index)},
                )
            )
            section_index += 1
            buffer = [para]
        else:
            buffer.append(para)
    if buffer:
        section_id = f"{source}-section-{section_index}"
        chunks.append(
            RuleChunk(
                id=section_id,
                text="\n\n".join(buffer).strip(),
                metadata={"rule_id": section_id, "source": source, "section": str(section_index)},
            )
        )
    return chunks

