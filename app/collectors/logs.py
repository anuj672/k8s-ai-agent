from kubernetes.client.exceptions import ApiException

from app.k8s_client import core


def _read_log(namespace, pod, container, previous):
    try:
        return core.read_namespaced_pod_log(
            name=pod, namespace=namespace, container=container,
            tail_lines=30, previous=previous,
        )
    except ApiException:
        return None  # container never started, or no previous run


def collect_logs(namespace: str, pods: list[dict]) -> list[dict]:
    results = []
    for pod in pods:
        for c in pod["containers"]:
            if c["ready"]:
                continue  # healthy container, skip
            previous = _read_log(namespace, pod["name"], c["name"], previous=True) \
                if c["restart_count"] > 0 else None
            current = _read_log(namespace, pod["name"], c["name"], previous=False)
            if previous or current:
                results.append({
                    "pod": pod["name"],
                    "container": c["name"],
                    "previous": previous,
                    "current": current,
                })
    return results