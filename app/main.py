"""k8s-ai-agent API.

Collects read-only evidence from a namespace, then asks Amazon Bedrock
for a root-cause analysis validated against a Pydantic schema.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from kubernetes.client.exceptions import ApiException
from pydantic import BaseModel, Field

from app.collectors.deployments import inspect_deployments
from app.collectors.events import collect_events
from app.collectors.logs import collect_logs
from app.collectors.network import inspect_services
from app.collectors.pods import inspect_pods
from app.k8s_client import core
from app.llm import GuardrailBlocked, diagnose

UI_FILE = Path(__file__).resolve().parent.parent / "ui" / "index.html"

app = FastAPI(title="k8s-ai-agent", version="1.0.0")


class InvestigateRequest(BaseModel):
    # Valid Kubernetes namespace name (DNS-1123 label): rejects junk before any API call
    namespace: str = Field(..., pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63)


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(UI_FILE)


@app.get("/healthz")
def healthz():
    """Liveness/readiness probe target. Deliberately does not call Kubernetes or Bedrock."""
    return {"status": "ok"}


@app.get("/namespaces")
def list_namespaces():
    """Namespace picker for the UI (needs `list namespaces` from the ClusterRole)."""
    try:
        return sorted(ns.metadata.name for ns in core.list_namespace().items)
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)


@app.post("/investigate")
def investigate(req: InvestigateRequest):
    ns = req.namespace

    # 1. Evidence (deterministic, read-only)
    try:
        pods = inspect_pods(ns)
        evidence = {
            "namespace": ns,
            "pods": pods,
            "deployments": inspect_deployments(ns),
            "services": inspect_services(ns, pods),
            "events": collect_events(ns),
            "logs": collect_logs(ns, pods),
        }
    except ApiException as e:
        # 403 here means the ServiceAccount's RBAC is missing a permission
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API: {e.reason}")

    # 2. Reasoning (Bedrock), validated against the schema
    try:
        diagnosis, usage = diagnose(evidence)
    except GuardrailBlocked as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"diagnosis": diagnosis, "usage": usage, "evidence": evidence}
