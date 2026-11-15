from app.k8s_client import core, discovery
import json

def _count_endpoints(namespace: str, service: str) -> int:
    # _preload_content=False returns raw JSON, avoiding a client bug where
    # EndpointSlices with no endpoints (endpoints: null) crash deserialization.
    resp = discovery.list_namespaced_endpoint_slice(
        namespace,
        label_selector=f"kubernetes.io/service-name={service}",
        _preload_content=False,
    )
    slices = json.loads(resp.data)["items"]
    return sum(len(s.get("endpoints") or []) for s in slices)


def inspect_services(namespace: str, pods: list[dict]) -> list[dict]:
    results = []
    for svc in core.list_namespaced_service(namespace).items:
        selector = svc.spec.selector or {}
        matching = [
            p["name"] for p in pods
            if selector and all(p["labels"].get(k) == v for k, v in selector.items())
        ]
        results.append({
            "name": svc.metadata.name,
            "selector": selector,
            "endpoints": _count_endpoints(namespace, svc.metadata.name),
            "matching_pods": matching,
            "pod_labels": {p["name"]: p["labels"] for p in pods} if not matching else None,
        })
    return results