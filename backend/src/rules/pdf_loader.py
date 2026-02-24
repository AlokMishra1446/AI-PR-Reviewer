from pathlib import Path
from typing import List

import pdfplumber


def load_pdf_text(path: Path) -> str:
    text_parts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            content = page.extract_text() or ""
            if content:
                text_parts.append(content)
    return "\n".join(text_parts)


def load_all_pdfs(rules_dir: Path) -> str:
    texts: List[str] = []
    for pdf_path in sorted(rules_dir.glob("*.pdf")):
        text = load_pdf_text(pdf_path)
        if text.strip():
            texts.append(text)
    return "\n\n".join(texts)

