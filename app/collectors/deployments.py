from app.k8s_client import apps


def inspect_deployments(namespace: str) -> list[dict]:
    results = []
    for d in apps.list_namespaced_deployment(namespace).items:
        results.append({
            "name": d.metadata.name,
            "desired_replicas": d.spec.replicas or 0,
            "available_replicas": d.status.available_replicas or 0,
            "images": [c.image for c in d.spec.template.spec.containers],
            "selector": d.spec.selector.match_labels or {},
        })
    return results