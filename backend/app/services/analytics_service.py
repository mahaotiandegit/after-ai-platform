from sqlalchemy import text
from sqlalchemy.orm import Session


def _scalar_int(db: Session, sql: str) -> int:
    value = db.execute(text(sql)).scalar_one()
    return int(value or 0)


def _scalar_float(db: Session, sql: str) -> float:
    value = db.execute(text(sql)).scalar_one()
    return float(value or 0)


def _count_distribution(db: Session, sql: str) -> list[dict]:
    rows = db.execute(text(sql)).mappings().all()
    return [
        {
            "label": str(row["label"]),
            "count": int(row["count"]),
        }
        for row in rows
    ]


def get_analytics_overview(db: Session) -> dict:
    orders_total = _scalar_int(db, "SELECT COUNT(*) FROM orders")
    tickets_total = _scalar_int(db, "SELECT COUNT(*) FROM tickets")
    tickets_open = _scalar_int(db, "SELECT COUNT(*) FROM tickets WHERE status = 'open'")
    tickets_high_priority = _scalar_int(db, "SELECT COUNT(*) FROM tickets WHERE priority = 'high'")
    refunds_pending = _scalar_int(db, "SELECT COUNT(*) FROM refunds WHERE status = 'pending'")
    documents_indexed = _scalar_int(db, "SELECT COUNT(*) FROM documents WHERE status = 'indexed'")
    avg_qa_latency_ms = _scalar_float(db, "SELECT COALESCE(AVG(latency_ms), 0) FROM qa_logs")

    ticket_status_distribution = _count_distribution(
        db,
        """
        SELECT status AS label, COUNT(*) AS count
        FROM tickets
        GROUP BY status
        ORDER BY count DESC
        """,
    )

    ticket_category_distribution = _count_distribution(
        db,
        """
        SELECT category AS label, COUNT(*) AS count
        FROM tickets
        GROUP BY category
        ORDER BY count DESC
        """,
    )

    refund_status_distribution = _count_distribution(
        db,
        """
        SELECT status AS label, COUNT(*) AS count
        FROM refunds
        GROUP BY status
        ORDER BY count DESC
        """,
    )

    return {
        "orders_total": orders_total,
        "tickets_total": tickets_total,
        "tickets_open": tickets_open,
        "tickets_high_priority": tickets_high_priority,
        "refunds_pending": refunds_pending,
        "documents_indexed": documents_indexed,
        "avg_qa_latency_ms": round(avg_qa_latency_ms, 2),
        "ticket_status_distribution": ticket_status_distribution,
        "ticket_category_distribution": ticket_category_distribution,
        "refund_status_distribution": refund_status_distribution,
    }