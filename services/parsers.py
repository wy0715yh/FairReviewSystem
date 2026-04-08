from __future__ import annotations

import io
from typing import Iterable, List

import docx
import PyPDF2


SUPPORTED_EXT = {".txt", ".docx", ".pdf"}


def read_uploaded_file(file_storage) -> str:
    name = (file_storage.filename or "").lower()
    try:
        if name.endswith(".docx"):
            data = file_storage.read()
            buf = io.BytesIO(data)
            d = docx.Document(buf)
            return "\n".join([p.text for p in d.paragraphs if p.text])
        if name.endswith(".pdf"):
            data = file_storage.read()
            buf = io.BytesIO(data)
            reader = PyPDF2.PdfReader(buf)
            parts = []
            for p in reader.pages:
                parts.append(p.extract_text() or "")
            return "\n".join(parts)
        if name.endswith(".txt"):
            return file_storage.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""
    return ""


def concat_text_input(text: str, files: Iterable) -> str:
    parts: List[str] = []
    if text and text.strip():
        parts.append(text.strip())
    for f in files or []:
        payload = read_uploaded_file(f)
        if payload.strip():
            parts.append(payload.strip())
    return "\n\n".join(parts).strip()
