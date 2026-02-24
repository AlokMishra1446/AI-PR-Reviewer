from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AddedLine:
    file_path: str
    line_number: int
    content: str
    hunk_context: str


def parse_unified_diff(diff_text: str, file_path: str) -> List[AddedLine]:
    added: List[AddedLine] = []
    current_new_line: Optional[int] = None
    hunk_lines: List[str] = []
    for raw_line in diff_text.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("@@"):
            parts = line.split()
            new_range = ""
            for part in parts:
                if part.startswith("+"):
                    new_range = part
                    break
            if "," in new_range:
                start_str = new_range[1:].split(",")[0]
            else:
                start_str = new_range[1:]
            current_new_line = int(start_str)
            hunk_lines = []
            continue
        if current_new_line is None:
            continue
        if line.startswith(" "):
            hunk_lines.append(line[1:])
            current_new_line += 1
        elif line.startswith("+"):
            content = line[1:]
            context_preview = "\n".join(hunk_lines[-3:])
            added.append(
                AddedLine(
                    file_path=file_path,
                    line_number=current_new_line,
                    content=content,
                    hunk_context=context_preview,
                )
            )
            current_new_line += 1
        elif line.startswith("-"):
            current_new_line += 0
        else:
            continue
    return added

