from __future__ import annotations

import hashlib
import math
import os
import re
import unicodedata


DEFAULT_DIMENSION = 384

def embedding_dimension()->int:
    raw=os.getenv("EMBEDDING_DIMENSION",str(DEFAULT_DIMENSION))
    try:
        value=int(raw)
    except ValueError:
        return DEFAULT_DIMENSION
    return value if value>0 else DEFAULT_DIMENSION

def embedding_dimension()->int:
    raw = os.getenv("EMBEDDING_DIMENSION", str(DEFAULT_DIMENSION))
    try:
        value=int(raw)
    except ValueError:
        return DEFAULT_DIMENSION
    return value if value>0 else DEFAULT_DIMENSION

def embedding_model_name()->str:
    return os.getenv("EMBEDDING_MODEL", f"local-hash-{embedding_dimension()}")

def _normalize_text(text:str)->str:
    text=unicodedata.normalize("NFKC",text or "")
    text=text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _is_cjk(ch:str)->bool:
    return "\u4e00" <= ch <= "\u9fff"

def _tokens(text:str)->list[str]:
    text=_normalize_text(text)

    ascii_tokens=re.findall(r"[a-z0-9_]+", text)
    cjk_chars=[ch for ch in text if _is_cjk(ch)]

    cjk_bigrams:list[str]=[]
    for i in range(len(cjk_chars) - 1):
        cjk_bigrams.append(cjk_chars[i] + cjk_chars[i + 1])
    
    tokens=ascii_tokens+cjk_chars+cjk_bigrams

    if not tokens and text:
        tokens=[text]

    return tokens

def embed_text(text:str,dimension:int | None=None)->list[float]:
    dim=dimension or embedding_dimension()
    vector=[0.0]*dim

    tokens=_tokens(text)
    if not tokens:
        return vector
    
    for token in tokens:
        digest=hashlib.blake2b(token.encode("utf-8"),digest_size=16).digest()

        idx=int.from_bytes(digest[:8],"big")%dim
        sign=1.0 if digest[8]%2==0 else -1.0

        weight = 1.0
        if len(token) >= 2:
            weight = 1.25

        vector[idx] += sign * weight
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector

    return [round(x / norm, 6) for x in vector]


def to_pgvector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"