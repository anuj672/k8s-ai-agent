from app.k8s_client import core


def inspect_pods(namespace: str) -> list[dict]:
    findings = []
    for pod in core.list_namespaced_pod(namespace).items:
        containers = []
        for cs in pod.status.container_statuses or []:
            waiting = cs.state.waiting
            last = cs.last_state.terminated if cs.last_state else None
            containers.append({
                "name": cs.name,
                "image": cs.image,
                "ready": cs.ready,
                "restart_count": cs.restart_count,
                "waiting_reason": waiting.reason if waiting else None,
                "last_exit_code": last.exit_code if last else None,
            })
        findings.append({
            "name": pod.metadata.name,
            "phase": pod.status.phase,
            "labels": pod.metadata.labels or {},
            "containers": containers,
        })
    return findings