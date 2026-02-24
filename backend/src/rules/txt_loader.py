from pathlib import Path
from typing import List


def load_txt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_all_txt(rules_dir: Path) -> str:
    texts: List[str] = []
    for txt_path in sorted(rules_dir.glob("*.txt")):
        text = load_txt_text(txt_path)
        if text.strip():
            texts.append(text)
    return "\n\n".join(texts)

