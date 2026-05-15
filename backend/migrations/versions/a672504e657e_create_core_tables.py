"""create core tables

Revision ID: a672504e657e
Revises:
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a672504e657e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username VARCHAR(64) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL DEFAULT '',
        role VARCHAR(32) NOT NULL DEFAULT 'agent',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_no VARCHAR(64) NOT NULL UNIQUE,
        customer_name VARCHAR(64) NOT NULL,
        customer_phone VARCHAR(32) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'paid',
        total_amount_cents INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS logistics (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_id UUID NOT NULL REFERENCES orders(id),
        carrier VARCHAR(64) NOT NULL,
        tracking_no VARCHAR(128) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'in_transit',
        latest_event TEXT,
        shipped_at TIMESTAMPTZ,
        delivered_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS refunds (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_id UUID NOT NULL REFERENCES orders(id),
        refund_no VARCHAR(64) NOT NULL UNIQUE,
        reason VARCHAR(255) NOT NULL,
        amount_cents INTEGER NOT NULL DEFAULT 0,
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticket_no VARCHAR(64) NOT NULL UNIQUE,
        order_id UUID REFERENCES orders(id),
        customer_question TEXT NOT NULL,
        category VARCHAR(64) NOT NULL,
        priority VARCHAR(32) NOT NULL DEFAULT 'medium',
        title VARCHAR(255) NOT NULL,
        summary TEXT NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'open',
        assignee_id UUID REFERENCES users(id),
        created_by_id UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title VARCHAR(255) NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_type VARCHAR(32) NOT NULL,
        storage_path VARCHAR(512) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
        uploaded_by_id UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        page_no INTEGER,
        token_count INTEGER NOT NULL DEFAULT 0,
        embedding vector(1536),
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS qa_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id),
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        citations JSONB NOT NULL DEFAULT '{}'::jsonb,
        latency_ms INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS feedbacks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        qa_log_id UUID REFERENCES qa_logs(id),
        ticket_id UUID REFERENCES tickets(id),
        user_id UUID REFERENCES users(id),
        rating INTEGER NOT NULL DEFAULT 0,
        comment TEXT,
        status VARCHAR(32) NOT NULL DEFAULT 'new',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_logistics_order_id ON logistics(order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refunds_order_id ON refunds(order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tickets_order_id ON tickets(order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts ON document_chunks USING GIN (to_tsvector('simple', content))")
    op.execute("CREATE INDEX IF NOT EXISTS idx_qa_logs_created_at ON qa_logs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_status ON feedbacks(status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feedbacks")
    op.execute("DROP TABLE IF EXISTS qa_logs")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS tickets")
    op.execute("DROP TABLE IF EXISTS refunds")
    op.execute("DROP TABLE IF EXISTS logistics")
    op.execute("DROP TABLE IF EXISTS orders")
    op.execute("DROP TABLE IF EXISTS users")
