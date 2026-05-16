from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.orders import router as orders_router
from app.api.v1.system import router as system_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.feedbacks import router as feedbacks_router
from app.api.v1.knowledge_llm import router as knowledge_llm_router
from app.middleware.ai_audit_middleware import AIAuditMiddleware

app = FastAPI(

    title="After AI Platform",
    description="E-commerce aftersales knowledge and ticket automation platform",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(AIAuditMiddleware)


app.include_router(system_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(feedbacks_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(knowledge_llm_router, prefix="/api/v1")


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": "after-ai-platform",
        "version": "0.1.0",
    }


# ticket ai classifier v1
from app.api.v1 import ticket_ai_classifier
app.include_router(ticket_ai_classifier.router, prefix="/api/v1")

# ai audit logs
from app.api.v1 import ai_audit
app.include_router(ai_audit.router, prefix="/api/v1")

# bad cases
from app.api.v1 import bad_cases
app.include_router(bad_cases.router, prefix="/api/v1")

# ai quality
from app.api.v1 import ai_quality
app.include_router(ai_quality.router, prefix="/api/v1/ai-quality")
