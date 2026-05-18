from __future__ import annotations

import re
from typing import Any


class Nl2sqlSafetyError(ValueError):
    pass


DEFAULT_ALLOWED_TABLES = {
    "orders",
    "logistics",
    "refunds",
    "tickets",
    "documents",
    "document_chunks",
    "qa_logs",
    "feedbacks",
}


class SqlSafetyResult(str):
    """
    兼容两种用法：
    1. 当成字符串 SQL 使用
    2. 通过 .sql / .safe_sql / .applied_limit / .tables_used 读取安全校验结果
    """

    def __new__(
        cls,
        sql: str,
        *,
        applied_limit: int | None = None,
        row_limit: int | None = None,
        tables: list[str] | None = None,
    ):
        obj = str.__new__(cls, sql)
        obj.sql = sql
        obj.safe_sql = sql
        obj.final_sql = sql
        obj.normalized_sql = sql
        obj.applied_limit = applied_limit
        obj.row_limit = row_limit
        obj.tables = tables or []
        obj.tables_used = obj.tables
        obj.ok = True
        return obj

    def dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "sql": self.sql,
            "safe_sql": self.safe_sql,
            "final_sql": self.final_sql,
            "normalized_sql": self.normalized_sql,
            "applied_limit": self.applied_limit,
            "row_limit": self.row_limit,
            "tables": self.tables,
            "tables_used": self.tables_used,
        }

    def model_dump(self) -> dict[str, Any]:
        return self.dict()

    def get(self, key: str, default: Any = None) -> Any:
        return self.dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.dict()[key]


_FORBIDDEN_PATTERNS = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\btruncate\b",
    r"\bcreate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcopy\b",
    r"\bexecute\b",
    r"\bcall\b",
    r"\bmerge\b",
    r"\bvacuum\b",
    r"\banalyze\b",
    r"\bcomment\b",
    r"\bpg_sleep\b",
    r"\binformation_schema\b",
    r"\bpg_catalog\b",
    r"\bpg_tables\b",
    r"\bpg_user\b",
    r"\bpg_shadow\b",
]


def _strip_trailing_semicolon(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def _extract_tables(sql: str) -> list[str]:
    lowered = sql.lower()
    tables: list[str] = []

    for match in re.finditer(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", lowered):
        table = match.group(1).split(".")[-1].strip('"')
        if table and table not in tables:
            tables.append(table)

    return tables


def _has_limit(sql: str) -> bool:
    return re.search(r"\blimit\s+(:[a-zA-Z_][a-zA-Z0-9_]*|\d+)\b", sql.lower()) is not None


def validate_select_sql(
    sql: str,
    *,
    row_limit: int | None = None,
    allowed_tables: set[str] | list[str] | tuple[str, ...] | None = None,
    **_: Any,
) -> SqlSafetyResult:
    if not isinstance(sql, str):
        raise Nl2sqlSafetyError("SQL must be a string")

    normalized = _strip_trailing_semicolon(sql)

    if not normalized:
        raise Nl2sqlSafetyError("SQL is empty")

    lowered = re.sub(r"\s+", " ", normalized.lower()).strip()

    if not lowered.startswith("select"):
        raise Nl2sqlSafetyError("Only SELECT SQL is allowed")

    if ";" in normalized:
        raise Nl2sqlSafetyError("Multiple SQL statements are not allowed")

    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise Nl2sqlSafetyError("SQL comments are not allowed")

    if re.search(r"\b(?:from|join)\s*\(", lowered):
        raise Nl2sqlSafetyError("Subquery is not allowed")

    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, lowered):
            raise Nl2sqlSafetyError(f"Forbidden SQL keyword: {pattern}")

    tables = _extract_tables(normalized)

    allowed = {str(t).lower() for t in (allowed_tables or DEFAULT_ALLOWED_TABLES)}
    illegal = [t for t in tables if t.lower() not in allowed]
    if illegal:
        raise Nl2sqlSafetyError(f"Table is not allowed: {', '.join(illegal)}")

    applied_limit: int | None = None
    safe_sql = normalized

    if row_limit is not None:
        try:
            applied_limit = max(1, min(int(row_limit), 100))
        except Exception as exc:
            raise Nl2sqlSafetyError(f"Invalid row_limit: {row_limit}") from exc

        if not _has_limit(lowered):
            safe_sql = f"{safe_sql}\nLIMIT :__safe_limit"

    return SqlSafetyResult(
        safe_sql,
        applied_limit=applied_limit,
        row_limit=row_limit,
        tables=tables,
    )