# tools/infra.py — Infrastructure monitoring and service control.
#
# system_health() — psutil metrics on the agent machine + /health pings on all
#   Xeon microservices (memory :8083, code-runner :8084, email :8085).
#   Returns a single combined status string. Non-fatal: service unreachable
#   is reported in the string, not raised.
#
# docker_restart(service) — restart an allowlisted Docker Compose service on
#   the agent machine via subprocess. Xeon services are excluded (would require
#   SSH). Rejects any service name not in the allowlist.


def system_health() -> str:
    # Implementation omitted.
    raise NotImplementedError


def docker_restart(service: str) -> str:
    # Implementation omitted.
    # Allowlist: services running locally on the agent machine only.
    # Xeon services are not restartable from here.
    raise NotImplementedError
