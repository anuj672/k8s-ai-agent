from app.k8s_client import core


def collect_events(namespace: str) -> list[dict]:
    results = []
    for e in core.list_namespaced_event(namespace).items:
        if e.type != "Warning":
            continue  # skip normal events like Scheduled, Pulled, Started
        results.append({
            "object": f"{e.involved_object.kind}/{e.involved_object.name}",
            "reason": e.reason,
            "message": (e.message or "")[:300],
            "count": e.count or 1,
        })
    return results