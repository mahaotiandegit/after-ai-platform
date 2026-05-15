from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import inspect, text


DEFAULT_SCENES = [
    "ticket_ai_classifier",
    "rag_ask_llm",
    "analytics_nl2sql",
]


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _has_table(db, table_name: str) -> bool:
    return inspect(db.bind).has_table(table_name)


def _columns(db, table_name: str) -> set[str]:
    if not _has_table(db, table_name):
        return set()
    return {col["name"] for col in inspect(db.bind).get_columns(table_name)}


def _scalar(db, sql: str, params: dict | None = None):
    return db.execute(text(sql), params or {}).scalar()


def _recent_rows(db, table_name: str, wanted_columns: list[str], where_sql: str = "", limit: int = 5):
    cols = _columns(db, table_name)
    selected = [c for c in wanted_columns if c in cols]

    if not selected:
        return []

    order_col = "created_at" if "created_at" in cols else selected[0]

    sql = f"""
        SELECT {", ".join(selected)}
        FROM {table_name}
        {where_sql}
        ORDER BY {order_col} DESC
        LIMIT :limit
    """

    rows = db.execute(text(sql), {"limit": limit}).mappings().all()
    return [
        {key: _jsonable(value) for key, value in dict(row).items()}
        for row in rows
    ]


def get_ai_quality_overview(db):
    has_ai_logs = _has_table(db, "ai_invocation_logs")
    has_bad_cases = _has_table(db, "bad_cases")

    ai_cols = _columns(db, "ai_invocation_logs") if has_ai_logs else set()
    bad_cols = _columns(db, "bad_cases") if has_bad_cases else set()

    total_invocations = 0
    successful_invocations = 0
    avg_latency_ms = 0.0
    scene_distribution = {scene: 0 for scene in DEFAULT_SCENES}
    recent_failed_invocations = []

    if has_ai_logs:
        total_invocations = int(_scalar(db, "SELECT COUNT(*) FROM ai_invocation_logs") or 0)

        if "success" in ai_cols:
            successful_invocations = int(
                _scalar(db, "SELECT COUNT(*) FROM ai_invocation_logs WHERE success = true") or 0
            )

        if "latency_ms" in ai_cols:
            avg_latency_ms = float(
                _scalar(db, "SELECT COALESCE(AVG(latency_ms), 0) FROM ai_invocation_logs") or 0
            )

        if "scene" in ai_cols:
            rows = db.execute(
                text("""
                    SELECT scene, COUNT(*) AS count
                    FROM ai_invocation_logs
                    GROUP BY scene
                    ORDER BY count DESC, scene ASC
                """)
            ).mappings().all()

            for row in rows:
                scene_distribution[str(row["scene"])] = int(row["count"])

        failed_where = "WHERE success = false" if "success" in ai_cols else ""
        recent_failed_invocations = _recent_rows(
            db,
            "ai_invocation_logs",
            [
                "id",
                "scene",
                "provider",
                "model",
                "success",
                "error_message",
                "latency_ms",
                "created_at",
            ],
            where_sql=failed_where,
            limit=5,
        )

    total_bad_cases = 0
    open_bad_cases = 0
    fixed_bad_cases = 0
    recent_bad_cases = []

    if has_bad_cases:
        total_bad_cases = int(_scalar(db, "SELECT COUNT(*) FROM bad_cases") or 0)

        if "status" in bad_cols:
            open_bad_cases = int(
                _scalar(db, "SELECT COUNT(*) FROM bad_cases WHERE status = 'open'") or 0
            )
            fixed_bad_cases = int(
                _scalar(db, "SELECT COUNT(*) FROM bad_cases WHERE status = 'fixed'") or 0
            )

        recent_bad_cases = _recent_rows(
            db,
            "bad_cases",
            [
                "id",
                "ai_log_id",
                "ai_invocation_log_id",
                "scene",
                "correction",
                "root_cause",
                "priority",
                "tags",
                "status",
                "created_at",
                "updated_at",
            ],
            limit=5,
        )

    success_rate = round(successful_invocations * 100 / total_invocations, 2) if total_invocations else 0.0
    bad_case_fix_rate = round(fixed_bad_cases * 100 / total_bad_cases, 2) if total_bad_cases else 0.0

    return {
        "total_invocations": total_invocations,
        "success_rate": success_rate,
        "avg_latency_ms": round(avg_latency_ms, 2),
        "scene_distribution": scene_distribution,
        "total_bad_cases": total_bad_cases,
        "open_bad_cases": open_bad_cases,
        "fixed_bad_cases": fixed_bad_cases,
        "bad_case_fix_rate": bad_case_fix_rate,
        "recent_bad_cases": recent_bad_cases,
        "recent_failed_invocations": recent_failed_invocations,
    }

def _clamp_days(days: int | None) -> int:
    if days is None:
        return 7
    try:
        days = int(days)
    except Exception:
        return 7
    if days < 1:
        return 7
    if days > 90:
        return 90
    return days


def get_ai_quality_trends(db, days: int = 7):
    """
    AI quality trend data for dashboard charts.

    Returns daily trends for:
    - invocation count
    - successful / failed invocation count
    - success rate
    - average latency
    - scene distribution by day
    - bad case creation count by day
    - bad case fixed count by day
    """
    days = _clamp_days(days)

    has_ai_logs = _has_table(db, "ai_invocation_logs")
    has_bad_cases = _has_table(db, "bad_cases")

    ai_cols = _columns(db, "ai_invocation_logs") if has_ai_logs else set()
    bad_cols = _columns(db, "bad_cases") if has_bad_cases else set()

    daily_invocations = []
    scene_daily_distribution = []
    daily_bad_cases = []

    if has_ai_logs and "created_at" in ai_cols:
        success_expr = "SUM(CASE WHEN success = true THEN 1 ELSE 0 END)" if "success" in ai_cols else "0"
        failed_expr = "SUM(CASE WHEN success = false THEN 1 ELSE 0 END)" if "success" in ai_cols else "0"
        avg_latency_expr = "COALESCE(AVG(latency_ms), 0)" if "latency_ms" in ai_cols else "0"

        rows = db.execute(
            text(f"""
                SELECT
                    DATE(created_at) AS day,
                    COUNT(*) AS total,
                    {success_expr} AS success_count,
                    {failed_expr} AS failed_count,
                    {avg_latency_expr} AS avg_latency_ms
                FROM ai_invocation_logs
                WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
                GROUP BY DATE(created_at)
                ORDER BY day ASC
            """),
            {"days": days},
        ).mappings().all()

        for row in rows:
            total = int(row["total"] or 0)
            success_count = int(row["success_count"] or 0)
            failed_count = int(row["failed_count"] or 0)
            avg_latency_ms = float(row["avg_latency_ms"] or 0)
            success_rate = round(success_count * 100 / total, 2) if total else 0.0

            daily_invocations.append({
                "day": _jsonable(row["day"]),
                "total": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_rate,
                "avg_latency_ms": round(avg_latency_ms, 2),
            })

        if "scene" in ai_cols:
            rows = db.execute(
                text("""
                    SELECT
                        DATE(created_at) AS day,
                        scene,
                        COUNT(*) AS count
                    FROM ai_invocation_logs
                    WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
                    GROUP BY DATE(created_at), scene
                    ORDER BY day ASC, scene ASC
                """),
                {"days": days},
            ).mappings().all()

            for row in rows:
                scene_daily_distribution.append({
                    "day": _jsonable(row["day"]),
                    "scene": row["scene"],
                    "count": int(row["count"] or 0),
                })

    if has_bad_cases and "created_at" in bad_cols:
        fixed_expr = (
            "SUM(CASE WHEN status = 'fixed' THEN 1 ELSE 0 END)"
            if "status" in bad_cols
            else "0"
        )

        rows = db.execute(
            text(f"""
                SELECT
                    DATE(created_at) AS day,
                    COUNT(*) AS created_count,
                    {fixed_expr} AS fixed_count
                FROM bad_cases
                WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
                GROUP BY DATE(created_at)
                ORDER BY day ASC
            """),
            {"days": days},
        ).mappings().all()

        for row in rows:
            created_count = int(row["created_count"] or 0)
            fixed_count = int(row["fixed_count"] or 0)
            daily_bad_cases.append({
                "day": _jsonable(row["day"]),
                "created_count": created_count,
                "fixed_count": fixed_count,
                "fix_rate": round(fixed_count * 100 / created_count, 2) if created_count else 0.0,
            })

    return {
        "days": days,
        "daily_invocations": daily_invocations,
        "scene_daily_distribution": scene_daily_distribution,
        "daily_bad_cases": daily_bad_cases,
    }

def _load_payload(value):
    import json

    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            if isinstance(loaded, dict):
                return loaded
            return {"value": loaded}
        except Exception:
            return {"raw": value}
    return {"raw": str(value)}


def _truthy_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _first_present(payload: dict, keys: list[str]):
    for key in keys:
        if key in payload:
            return payload.get(key)
    return None


def _evaluate_rag_ask_llm(output_payload: dict):
    issues = []
    suggestions = []

    answer = output_payload.get("answer")
    citations = output_payload.get("citations")
    hits = output_payload.get("hits")

    if not _truthy_text(answer):
        issues.append("answer is empty")
        suggestions.append("确保 RAG 链路返回可读 answer，而不是只返回检索 hits。")
    elif len(answer.strip()) < 30:
        issues.append("answer is too short")
        suggestions.append("补充适用条件、处理动作和升级条件，避免回答过短。")

    if not citations:
        issues.append("citations is empty")
        suggestions.append("RAG 回答必须返回引用来源，便于客服追溯规则出处。")

    if not hits:
        issues.append("hits is empty")
        suggestions.append("检查知识检索召回结果，避免 LLM 无依据生成。")

    sop_keywords = ["适用条件", "排除条件", "处理动作", "升级条件"]
    if _truthy_text(answer):
        matched = [kw for kw in sop_keywords if kw in answer]
        if len(matched) < 2:
            issues.append("answer lacks structured SOP fields")
            suggestions.append("Prompt 应强制输出：适用条件、排除条件、处理动作、升级条件。")

    return issues, suggestions


def _evaluate_ticket_ai_classifier(output_payload: dict):
    issues = []
    suggestions = []

    required_fields = ["category", "priority", "title", "summary"]
    for field in required_fields:
        if not _truthy_text(output_payload.get(field)):
            issues.append(f"{field} is missing")
            suggestions.append(f"工单 AI 分类结果必须包含 {field}。")

    priority = output_payload.get("priority")
    if priority and priority not in ["low", "medium", "high", "urgent"]:
        issues.append("priority is invalid")
        suggestions.append("priority 应限制在 low / medium / high / urgent。")

    if not _truthy_text(output_payload.get("recommended_action")):
        issues.append("recommended_action is missing")
        suggestions.append("分类结果建议返回 recommended_action，便于客服直接处理。")

    return issues, suggestions


def _evaluate_analytics_nl2sql(output_payload: dict):
    issues = []
    suggestions = []

    sql = output_payload.get("sql")
    summary = output_payload.get("summary")

    if not _truthy_text(sql):
        issues.append("sql is empty")
        suggestions.append("NL2SQL 必须返回 sql 字段。")
    else:
        normalized_sql = sql.strip().lower()
        dangerous_keywords = [
            "insert ",
            "update ",
            "delete ",
            "drop ",
            "alter ",
            "truncate ",
            "create ",
            "grant ",
            "revoke ",
            "copy ",
        ]

        if not normalized_sql.startswith("select"):
            issues.append("sql is not read-only select")
            suggestions.append("NL2SQL 只允许生成 SELECT 查询。")

        if any(keyword in normalized_sql for keyword in dangerous_keywords):
            issues.append("sql contains dangerous keyword")
            suggestions.append("拦截所有写入、删表、改表、授权类 SQL。")

    if not _truthy_text(summary):
        issues.append("summary is missing")
        suggestions.append("运营问数应返回自然语言 summary，不能只返回表格。")

    if "columns" not in output_payload:
        issues.append("columns is missing")
        suggestions.append("NL2SQL 返回结果应包含 columns，便于前端渲染表格。")

    if "rows" not in output_payload:
        issues.append("rows is missing")
        suggestions.append("NL2SQL 返回结果应包含 rows，便于运营复核数据。")

    return issues, suggestions




def _iter_payload_dicts(value, max_depth: int = 8):
    if max_depth < 0:
        return

    if isinstance(value, dict):
        yield value

        preferred_keys = [
            "output_payload",
            "payload",
            "result",
            "data",
            "response",
            "body",
            "content",
            "output",
            "message",
            "items",
        ]

        for key in preferred_keys:
            if key in value:
                yield from _iter_payload_dicts(value[key], max_depth - 1)

        for key, child in value.items():
            if key not in preferred_keys:
                yield from _iter_payload_dicts(child, max_depth - 1)

    elif isinstance(value, list):
        for child in value[:5]:
            yield from _iter_payload_dicts(child, max_depth - 1)


def _candidate_score(candidate: dict, expected_keys: set[str]) -> int:
    score = 0

    for key in expected_keys:
        if key in candidate and candidate.get(key) not in [None, "", [], {}]:
            score += 10

    # 常见包装字段优先级降低，业务字段优先级升高
    business_bonus_keys = {
        "answer",
        "citations",
        "hits",
        "sql",
        "columns",
        "rows",
        "summary",
        "category",
        "priority",
        "title",
        "recommended_action",
    }

    for key in business_bonus_keys:
        if key in candidate and candidate.get(key) not in [None, "", [], {}]:
            score += 2

    return score


def _find_best_payload_candidate(payload: dict, expected_keys: set[str]) -> dict:
    best = payload
    best_score = _candidate_score(payload, expected_keys)

    for candidate in _iter_payload_dicts(payload):
        score = _candidate_score(candidate, expected_keys)
        if score > best_score:
            best = candidate
            best_score = score

    return best


def _normalize_ai_output_payload(scene: str | None, payload: dict) -> dict:
    """
    兼容 AI 审计日志中常见的 output_payload 包装结构。

    支持：
    - 顶层字段
    - result/data/response/body/output/payload 嵌套字段
    - list 中第一层结果字段

    目标是让质量评估读取“真正业务输出”，避免把外层审计包装误判成空结果。
    """
    if not isinstance(payload, dict):
        return {}

    if scene == "rag_ask_llm":
        expected = {"answer", "citations", "hits"}
    elif scene == "analytics_nl2sql":
        expected = {"sql", "columns", "rows", "summary"}
    elif scene == "ticket_ai_classifier":
        expected = {"category", "priority", "title", "summary", "recommended_action"}
    else:
        expected = {
            "answer",
            "citations",
            "hits",
            "sql",
            "columns",
            "rows",
            "summary",
            "category",
            "priority",
            "title",
        }

    candidate = _find_best_payload_candidate(payload, expected)

    # 有些结构是 {"result": {"data": {...}}, "success": true}
    # 如果候选仍然没有关键字段，再尝试把所有嵌套 dict 的业务字段合并出来。
    if _candidate_score(candidate, expected) == 0:
        merged = {}
        for item in _iter_payload_dicts(payload):
            for key in expected:
                if key in item and key not in merged:
                    merged[key] = item.get(key)
        if merged:
            return merged

    return candidate


def _evaluate_ai_invocation(row: dict):
    scene = row.get("scene")
    success = row.get("success")
    error_message = row.get("error_message")
    raw_output_payload = _load_payload(row.get("output_payload"))
    output_payload = _normalize_ai_output_payload(scene, raw_output_payload)

    issues = []
    suggestions = []

    if success is False:
        issues.append("ai invocation failed")
        if error_message:
            issues.append(f"error: {error_message}")
        suggestions.append("优先排查 provider 调用、Prompt 输入和异常捕获。")

    if not output_payload:
        issues.append("output_payload is empty")
        suggestions.append("AI 调用必须落库 output_payload，便于审计和复盘。")

    if scene == "rag_ask_llm":
        sub_issues, sub_suggestions = _evaluate_rag_ask_llm(output_payload)
        issues.extend(sub_issues)
        suggestions.extend(sub_suggestions)
    elif scene == "ticket_ai_classifier":
        sub_issues, sub_suggestions = _evaluate_ticket_ai_classifier(output_payload)
        issues.extend(sub_issues)
        suggestions.extend(sub_suggestions)
    elif scene == "analytics_nl2sql":
        sub_issues, sub_suggestions = _evaluate_analytics_nl2sql(output_payload)
        issues.extend(sub_issues)
        suggestions.extend(sub_suggestions)
    else:
        issues.append("unknown scene")
        suggestions.append("为新的 AI 场景补充质量评估规则。")

    score = max(0, 100 - len(set(issues)) * 15)

    if success is False:
        score = min(score, 40)

    if score >= 85 and not issues:
        status = "pass"
    elif score >= 60:
        status = "warn"
    else:
        status = "fail"

    return {
        "score": score,
        "status": status,
        "issues": list(dict.fromkeys(issues)),
        "suggestions": list(dict.fromkeys(suggestions)),
    }


def run_recent_ai_quality_evaluations(db, limit: int = 20, force: bool = False):
    import json

    limit = max(1, min(int(limit or 20), 100))

    if not _has_table(db, "ai_invocation_logs"):
        return {
            "requested_limit": limit,
            "evaluated_count": 0,
            "items": [],
            "message": "ai_invocation_logs table not found",
        }

    if not _has_table(db, "ai_quality_evaluations"):
        return {
            "requested_limit": limit,
            "evaluated_count": 0,
            "items": [],
            "message": "ai_quality_evaluations table not found, run alembic upgrade head first",
        }

    if force:
        rows = db.execute(
            text("""
                SELECT
                    l.id,
                    l.scene,
                    l.provider,
                    l.model,
                    l.success,
                    l.error_message,
                    l.output_payload,
                    l.created_at
                FROM ai_invocation_logs l
                ORDER BY l.created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()
    else:
        rows = db.execute(
            text("""
                SELECT
                    l.id,
                    l.scene,
                    l.provider,
                    l.model,
                    l.success,
                    l.error_message,
                    l.output_payload,
                    l.created_at
                FROM ai_invocation_logs l
                LEFT JOIN ai_quality_evaluations e ON e.ai_log_id = l.id
                WHERE e.id IS NULL
                ORDER BY l.created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()

    items = []

    for row in rows:
        row_dict = dict(row)
        result = _evaluate_ai_invocation(row_dict)

        inserted = db.execute(
            text("""
                INSERT INTO ai_quality_evaluations (
                    ai_log_id,
                    scene,
                    provider,
                    model,
                    score,
                    status,
                    issues,
                    suggestions
                )
                VALUES (
                    :ai_log_id,
                    :scene,
                    :provider,
                    :model,
                    :score,
                    :status,
                    CAST(:issues AS JSONB),
                    CAST(:suggestions AS JSONB)
                )
                ON CONFLICT (ai_log_id) DO UPDATE SET
                    score = EXCLUDED.score,
                    status = EXCLUDED.status,
                    issues = EXCLUDED.issues,
                    suggestions = EXCLUDED.suggestions,
                    evaluated_at = now()
                RETURNING
                    id,
                    ai_log_id,
                    scene,
                    provider,
                    model,
                    score,
                    status,
                    issues,
                    suggestions,
                    evaluated_at,
                    created_at
            """),
            {
                "ai_log_id": row_dict["id"],
                "scene": row_dict.get("scene") or "unknown",
                "provider": row_dict.get("provider"),
                "model": row_dict.get("model"),
                "score": result["score"],
                "status": result["status"],
                "issues": json.dumps(result["issues"], ensure_ascii=False),
                "suggestions": json.dumps(result["suggestions"], ensure_ascii=False),
            },
        ).mappings().one()

        items.append({key: _jsonable(value) for key, value in dict(inserted).items()})

    db.commit()

    return {
        "requested_limit": limit,
        "force": bool(force),
        "evaluated_count": len(items),
        "items": items,
    }


def list_ai_quality_evaluations(db, limit: int = 20, status: str | None = None, scene: str | None = None):
    limit = max(1, min(int(limit or 20), 100))

    if not _has_table(db, "ai_quality_evaluations"):
        return {
            "total": 0,
            "items": [],
            "message": "ai_quality_evaluations table not found",
        }

    where = []
    params = {"limit": limit}

    if status:
        where.append("status = :status")
        params["status"] = status

    if scene:
        where.append("scene = :scene")
        params["scene"] = scene

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    total = int(
        db.execute(
            text(f"SELECT COUNT(*) FROM ai_quality_evaluations {where_sql}"),
            params,
        ).scalar()
        or 0
    )

    rows = db.execute(
        text(f"""
            SELECT
                id,
                ai_log_id,
                scene,
                provider,
                model,
                score,
                status,
                issues,
                suggestions,
                evaluated_at,
                created_at
            FROM ai_quality_evaluations
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        params,
    ).mappings().all()

    return {
        "total": total,
        "items": [
            {key: _jsonable(value) for key, value in dict(row).items()}
            for row in rows
        ],
    }

def get_ai_quality_evaluation_summary(db, recent_limit: int = 5, top_issue_limit: int = 10):
    """
    Aggregate AI quality evaluation results for dashboard.

    Returns:
    - total evaluations
    - pass / warn / fail count
    - average score
    - status distribution
    - scene-level score summary
    - most common issues
    - recent high-risk evaluations
    """
    recent_limit = max(1, min(int(recent_limit or 5), 20))
    top_issue_limit = max(1, min(int(top_issue_limit or 10), 50))

    if not _has_table(db, "ai_quality_evaluations"):
        return {
            "total_evaluations": 0,
            "pass_count": 0,
            "warn_count": 0,
            "fail_count": 0,
            "average_score": 0.0,
            "status_distribution": {},
            "scene_score_summary": [],
            "top_issues": [],
            "recent_high_risk_evaluations": [],
            "message": "ai_quality_evaluations table not found",
        }

    total_row = db.execute(
        text("""
            SELECT
                COUNT(*) AS total,
                COALESCE(AVG(score), 0) AS average_score,
                SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) AS pass_count,
                SUM(CASE WHEN status = 'warn' THEN 1 ELSE 0 END) AS warn_count,
                SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) AS fail_count
            FROM ai_quality_evaluations
        """)
    ).mappings().one()

    total_evaluations = int(total_row["total"] or 0)
    pass_count = int(total_row["pass_count"] or 0)
    warn_count = int(total_row["warn_count"] or 0)
    fail_count = int(total_row["fail_count"] or 0)
    average_score = round(float(total_row["average_score"] or 0), 2)

    status_rows = db.execute(
        text("""
            SELECT status, COUNT(*) AS count
            FROM ai_quality_evaluations
            GROUP BY status
            ORDER BY count DESC, status ASC
        """)
    ).mappings().all()

    status_distribution = {
        str(row["status"]): int(row["count"] or 0)
        for row in status_rows
    }

    for default_status in ["pass", "warn", "fail"]:
        status_distribution.setdefault(default_status, 0)

    scene_rows = db.execute(
        text("""
            SELECT
                scene,
                COUNT(*) AS total,
                COALESCE(AVG(score), 0) AS average_score,
                SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) AS pass_count,
                SUM(CASE WHEN status = 'warn' THEN 1 ELSE 0 END) AS warn_count,
                SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) AS fail_count
            FROM ai_quality_evaluations
            GROUP BY scene
            ORDER BY total DESC, scene ASC
        """)
    ).mappings().all()

    scene_score_summary = []
    for row in scene_rows:
        scene_score_summary.append({
            "scene": row["scene"],
            "total": int(row["total"] or 0),
            "average_score": round(float(row["average_score"] or 0), 2),
            "pass_count": int(row["pass_count"] or 0),
            "warn_count": int(row["warn_count"] or 0),
            "fail_count": int(row["fail_count"] or 0),
        })

    top_issue_rows = db.execute(
        text("""
            SELECT issue, COUNT(*) AS count
            FROM ai_quality_evaluations,
                 jsonb_array_elements_text(issues) AS issue
            GROUP BY issue
            ORDER BY count DESC, issue ASC
            LIMIT :limit
        """),
        {"limit": top_issue_limit},
    ).mappings().all()

    top_issues = [
        {
            "issue": row["issue"],
            "count": int(row["count"] or 0),
        }
        for row in top_issue_rows
    ]

    recent_rows = db.execute(
        text("""
            SELECT
                id,
                ai_log_id,
                scene,
                provider,
                model,
                score,
                status,
                issues,
                suggestions,
                evaluated_at,
                created_at
            FROM ai_quality_evaluations
            WHERE status IN ('fail', 'warn')
            ORDER BY
                CASE WHEN status = 'fail' THEN 0 ELSE 1 END,
                score ASC,
                created_at DESC
            LIMIT :limit
        """),
        {"limit": recent_limit},
    ).mappings().all()

    recent_high_risk_evaluations = [
        {key: _jsonable(value) for key, value in dict(row).items()}
        for row in recent_rows
    ]

    return {
        "total_evaluations": total_evaluations,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "average_score": average_score,
        "status_distribution": status_distribution,
        "scene_score_summary": scene_score_summary,
        "top_issues": top_issues,
        "recent_high_risk_evaluations": recent_high_risk_evaluations,
    }

def _ensure_json_list(value):
    import json

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            if isinstance(loaded, list):
                return loaded
            return [loaded]
        except Exception:
            return [value]

    return [value]


def _bad_case_column_types(db) -> dict[str, str]:
    if not _has_table(db, "bad_cases"):
        return {}

    rows = db.execute(
        text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'bad_cases'
        """)
    ).mappings().all()

    return {
        row["column_name"]: row["udt_name"] or row["data_type"]
        for row in rows
    }


def _fetch_bad_case_by_id(db, bad_case_id):
    cols = _columns(db, "bad_cases")
    if not cols:
        return None

    wanted = [
        "id",
        "ai_log_id",
        "ai_invocation_log_id",
        "scene",
        "correction",
        "root_cause",
        "priority",
        "tags",
        "status",
        "created_at",
        "updated_at",
    ]
    selected = [c for c in wanted if c in cols]

    if not selected:
        return None

    row = db.execute(
        text(f"""
            SELECT {", ".join(selected)}
            FROM bad_cases
            WHERE id::text = :id
            LIMIT 1
        """),
        {"id": str(bad_case_id)},
    ).mappings().first()

    if not row:
        return None

    return {key: _jsonable(value) for key, value in dict(row).items()}


def _find_existing_bad_case_for_evaluation(db, evaluation_id, ai_log_id=None):
    if not _has_table(db, "bad_cases"):
        return None

    cols = _columns(db, "bad_cases")
    where_parts = []
    params = {}

    if "tags" in cols:
        where_parts.append("tags::text LIKE :evaluation_tag")
        params["evaluation_tag"] = f"%ai_quality_evaluation:{evaluation_id}%"

    if ai_log_id is not None and "ai_log_id" in cols:
        where_parts.append("ai_log_id::text = :ai_log_id_text")
        params["ai_log_id_text"] = str(ai_log_id)

    if ai_log_id is not None and "ai_invocation_log_id" in cols:
        where_parts.append("ai_invocation_log_id::text = :ai_log_id_text")
        params["ai_log_id_text"] = str(ai_log_id)

    if not where_parts:
        return None

    row = db.execute(
        text(f"""
            SELECT id
            FROM bad_cases
            WHERE {" OR ".join(where_parts)}
            ORDER BY created_at DESC
            LIMIT 1
        """),
        params,
    ).mappings().first()

    if not row:
        return None

    return _fetch_bad_case_by_id(db, row["id"])


def _load_ai_quality_evaluation(db, evaluation_id):
    if not _has_table(db, "ai_quality_evaluations"):
        return None

    row = db.execute(
        text("""
            SELECT
                id,
                ai_log_id,
                scene,
                provider,
                model,
                score,
                status,
                issues,
                suggestions,
                evaluated_at,
                created_at
            FROM ai_quality_evaluations
            WHERE id::text = :evaluation_id
            LIMIT 1
        """),
        {"evaluation_id": str(evaluation_id)},
    ).mappings().first()

    if not row:
        return None

    return dict(row)


def _build_bad_case_payload_from_evaluation(evaluation: dict):
    issues = _ensure_json_list(evaluation.get("issues"))
    suggestions = _ensure_json_list(evaluation.get("suggestions"))

    score = int(evaluation.get("score") or 0)
    status = evaluation.get("status") or "unknown"
    scene = evaluation.get("scene") or "unknown"

    if status == "fail" or score <= 40:
        priority = "high"
    elif score <= 60:
        priority = "medium"
    else:
        priority = "low"

    root_cause = "；".join(str(x) for x in issues[:6] if str(x).strip())
    if not root_cause:
        root_cause = f"AI quality evaluation status={status}, score={score}"

    correction = "；".join(str(x) for x in suggestions[:6] if str(x).strip())
    if not correction:
        correction = "根据 AI 质量评估结果优化 prompt、工具调用、输出结构或异常处理。"

    tags = [
        "ai_quality",
        "auto_created",
        f"ai_quality_evaluation:{evaluation.get('id')}",
        f"ai_log:{evaluation.get('ai_log_id')}",
        f"scene:{scene}",
        f"status:{status}",
        f"score:{score}",
    ]

    return {
        "scene": scene,
        "ai_log_id": evaluation.get("ai_log_id"),
        "correction": correction,
        "root_cause": root_cause,
        "priority": priority,
        "tags": tags,
        "status": "open",
    }


def _insert_bad_case_from_payload(db, payload: dict):
    import json
    import uuid

    if not _has_table(db, "bad_cases"):
        raise RuntimeError("bad_cases table not found")

    cols = _columns(db, "bad_cases")
    col_types = _bad_case_column_types(db)

    insert_values = {}

    if "id" in cols:
        insert_values["id"] = str(uuid.uuid4())

    if "scene" in cols:
        insert_values["scene"] = payload["scene"]

    if "ai_log_id" in cols:
        insert_values["ai_log_id"] = payload["ai_log_id"]

    if "ai_invocation_log_id" in cols:
        insert_values["ai_invocation_log_id"] = payload["ai_log_id"]

    if "correction" in cols:
        insert_values["correction"] = payload["correction"]

    if "root_cause" in cols:
        insert_values["root_cause"] = payload["root_cause"]

    if "priority" in cols:
        insert_values["priority"] = payload["priority"]

    if "status" in cols:
        insert_values["status"] = payload["status"]

    if "tags" in cols:
        insert_values["tags"] = payload["tags"]

    if not insert_values:
        raise RuntimeError("bad_cases has no compatible columns for insertion")

    columns = []
    placeholders = []
    params = {}

    for key, value in insert_values.items():
        columns.append(key)

        if key == "tags":
            tag_type = col_types.get("tags", "")
            if tag_type in ["json", "jsonb"]:
                placeholders.append("CAST(:tags AS JSONB)")
                params["tags"] = json.dumps(value, ensure_ascii=False)
            else:
                placeholders.append(":tags")
                params["tags"] = ",".join(str(x) for x in value)
        else:
            placeholders.append(f":{key}")
            params[key] = value

    returning_wanted = [
        "id",
        "ai_log_id",
        "ai_invocation_log_id",
        "scene",
        "correction",
        "root_cause",
        "priority",
        "tags",
        "status",
        "created_at",
        "updated_at",
    ]
    returning_cols = [c for c in returning_wanted if c in cols]

    row = db.execute(
        text(f"""
            INSERT INTO bad_cases ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            RETURNING {", ".join(returning_cols)}
        """),
        params,
    ).mappings().one()

    return {key: _jsonable(value) for key, value in dict(row).items()}


def create_bad_case_from_ai_quality_evaluation(db, evaluation_id: str):
    evaluation = _load_ai_quality_evaluation(db, evaluation_id)

    if not evaluation:
        return {
            "action": "not_found",
            "message": "ai quality evaluation not found",
            "evaluation_id": str(evaluation_id),
            "bad_case": None,
        }

    score = int(evaluation.get("score") or 0)
    status = evaluation.get("status") or "unknown"

    if status != "fail" and score > 60:
        return {
            "action": "skipped",
            "reason": "evaluation is not high risk",
            "evaluation_id": _jsonable(evaluation["id"]),
            "score": score,
            "status": status,
            "bad_case": None,
        }

    existing = _find_existing_bad_case_for_evaluation(
        db,
        evaluation_id=evaluation["id"],
        ai_log_id=evaluation.get("ai_log_id"),
    )

    if existing:
        return {
            "action": "skipped",
            "reason": "bad case already exists for this evaluation or ai log",
            "evaluation_id": _jsonable(evaluation["id"]),
            "bad_case": existing,
        }

    payload = _build_bad_case_payload_from_evaluation(evaluation)
    bad_case = _insert_bad_case_from_payload(db, payload)
    db.commit()

    return {
        "action": "created",
        "evaluation_id": _jsonable(evaluation["id"]),
        "bad_case": bad_case,
    }


def auto_create_bad_cases_from_high_risk_evaluations(db, score_lte: int = 60, limit: int = 20):
    score_lte = max(0, min(int(score_lte or 60), 100))
    limit = max(1, min(int(limit or 20), 100))

    if not _has_table(db, "ai_quality_evaluations"):
        return {
            "score_lte": score_lte,
            "limit": limit,
            "created_count": 0,
            "skipped_count": 0,
            "items": [],
            "message": "ai_quality_evaluations table not found",
        }

    rows = db.execute(
        text("""
            SELECT
                id,
                ai_log_id,
                scene,
                provider,
                model,
                score,
                status,
                issues,
                suggestions,
                evaluated_at,
                created_at
            FROM ai_quality_evaluations
            WHERE status = 'fail'
               OR score <= :score_lte
            ORDER BY
                CASE WHEN status = 'fail' THEN 0 ELSE 1 END,
                score ASC,
                created_at DESC
            LIMIT :limit
        """),
        {
            "score_lte": score_lte,
            "limit": limit,
        },
    ).mappings().all()

    items = []
    created_count = 0
    skipped_count = 0

    for row in rows:
        evaluation = dict(row)
        existing = _find_existing_bad_case_for_evaluation(
            db,
            evaluation_id=evaluation["id"],
            ai_log_id=evaluation.get("ai_log_id"),
        )

        if existing:
            skipped_count += 1
            items.append({
                "action": "skipped",
                "reason": "bad case already exists for this evaluation or ai log",
                "evaluation_id": _jsonable(evaluation["id"]),
                "bad_case": existing,
            })
            continue

        payload = _build_bad_case_payload_from_evaluation(evaluation)
        bad_case = _insert_bad_case_from_payload(db, payload)
        created_count += 1

        items.append({
            "action": "created",
            "evaluation_id": _jsonable(evaluation["id"]),
            "bad_case": bad_case,
        })

    db.commit()

    return {
        "score_lte": score_lte,
        "limit": limit,
        "matched_count": len(rows),
        "created_count": created_count,
        "skipped_count": skipped_count,
        "items": items,
    }
