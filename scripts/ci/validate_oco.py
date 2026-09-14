\
#!/usr/bin/env python3
"""OCO-specific static validation after Kustomize rendering."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


class CheckError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def load_yaml_documents(path: Path) -> list[dict]:
    documents: list[dict] = []
    with path.open(encoding="utf-8") as stream:
        for document in yaml.safe_load_all(stream):
            if isinstance(document, dict):
                documents.append(document)
    return documents


def by_kind(documents: list[dict], kind: str) -> list[dict]:
    return [document for document in documents if document.get("kind") == kind]


def named(documents: list[dict], kind: str, name: str) -> dict:
    for document in documents:
        if document.get("kind") == kind and document.get("metadata", {}).get("name") == name:
            return document
    raise CheckError(f"missing {kind}/{name}")


def deployment_container(deployment: dict, container_name: str) -> dict:
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    for container in containers:
        if container.get("name") == container_name:
            return container
    raise CheckError(
        f"Deployment/{deployment['metadata']['name']} missing container {container_name}"
    )


def validate_taskfile(root: Path) -> None:
    document = yaml.safe_load((root / "Taskfile.yml").read_text(encoding="utf-8"))
    require(isinstance(document, dict), "Taskfile.yml must be a mapping")
    require(set(document) <= {"version", "tasks"}, "Taskfile.yml has keys outside version/tasks")
    require(str(document.get("version")) == "3", "Taskfile.yml must use Task v3")
    tasks = document.get("tasks")
    require(isinstance(tasks, dict), "Taskfile.yml tasks must be a mapping")

    expected = {
        "backend:up",
        "backend:down",
        "backend:status",
        "backend:smoke",
        "backend:baseline",
        "platform:up",
        "platform:status",
        "ci:validate",
    }
    missing = sorted(expected - set(tasks))
    require(not missing, f"Taskfile.yml missing tasks: {', '.join(missing)}")


def validate_backend(documents: list[dict]) -> None:
    deployments = by_kind(documents, "Deployment")
    names = {item["metadata"]["name"] for item in deployments}
    require(
        names == {"alloy", "victoriametrics", "victorialogs", "tempo"},
        f"backend Deployments must be exactly alloy/victoriametrics/victorialogs/tempo; got {sorted(names)}",
    )
    require(not by_kind(documents, "DaemonSet"), "backend must not contain a DaemonSet")

    prohibited = {
        item["metadata"]["name"]
        for item in deployments
        if "prometheus" in item["metadata"]["name"].lower()
        or "loki" in item["metadata"]["name"].lower()
    }
    require(not prohibited, f"prohibited duplicate backend workloads: {sorted(prohibited)}")

    for deployment in deployments:
        for container in deployment["spec"]["template"]["spec"].get("containers", []):
            image = container.get("image", "")
            require(image and ":" in image.rsplit("/", 1)[-1], f"{image!r} is not explicitly tagged")
            require(not image.endswith(":latest"), f"{image!r} must not use latest")
            resources = container.get("resources", {})
            require(resources.get("requests"), f"{deployment['metadata']['name']}/{container['name']} missing requests")
            require(resources.get("limits"), f"{deployment['metadata']['name']}/{container['name']} missing limits")

    pvc_names = {item["metadata"]["name"] for item in by_kind(documents, "PersistentVolumeClaim")}
    require(
        {"victoriametrics-data", "victorialogs-data", "tempo-data"} <= pvc_names,
        f"backend PVC set incomplete: {sorted(pvc_names)}",
    )

    policies = by_kind(documents, "NetworkPolicy")
    require(len(policies) >= 4, "backend must render explicit NetworkPolicy objects")

    vm = deployment_container(named(documents, "Deployment", "victoriametrics"), "victoriametrics")
    vm_args = set(vm.get("args", []))
    require("-retentionPeriod=30d" in vm_args, "VictoriaMetrics retention must be 30d")
    require(
        "-storage.minFreeDiskSpaceBytes=10GiB" in vm_args,
        "VictoriaMetrics must reserve 10GiB free space on the 50Gi PVC",
    )
    require(
        not any("storage.maxDiskSpaceUsageBytes" in arg for arg in vm_args),
        "VictoriaMetrics does not use storage.maxDiskSpaceUsageBytes",
    )

    vl = deployment_container(named(documents, "Deployment", "victorialogs"), "victorialogs")
    vl_args = set(vl.get("args", []))
    require("-retentionPeriod=14d" in vl_args, "VictoriaLogs retention must be 14d")
    require(
        "-retention.maxDiskSpaceUsageBytes=30GiB" in vl_args,
        "VictoriaLogs disk-retention cap must be 30GiB",
    )
    require(
        "-storage.minFreeDiskSpaceBytes=5GiB" in vl_args,
        "VictoriaLogs must reserve 5GiB free space",
    )
    require(
        not any(arg.startswith("-storage.maxDiskSpaceUsageBytes=") for arg in vl_args),
        "VictoriaLogs disk cap must use retention.maxDiskSpaceUsageBytes",
    )

    alloy = named(documents, "Deployment", "alloy")
    alloy_container = deployment_container(alloy, "alloy")
    mounts = {
        mount.get("name"): mount
        for mount in alloy_container.get("volumeMounts", [])
    }
    for mount_name in ("pod-logs", "container-logs"):
        require(mount_name in mounts, f"Alloy missing {mount_name} mount")
        require(mounts[mount_name].get("readOnly") is True, f"Alloy {mount_name} mount must be read-only")


def validate_console(documents: list[dict]) -> None:
    configmap = named(documents, "ConfigMap", "oco-shared-datasources")
    data = configmap.get("data", {})
    require(data, "shared datasource ConfigMap has no data")
    payload = next(iter(data.values()))
    datasource_doc = yaml.safe_load(payload)
    datasources = datasource_doc.get("datasources", [])
    uids = {datasource.get("uid") for datasource in datasources}
    require(
        uids == {"victoriametrics", "victorialogs", "tempo"},
        f"shared datasource UIDs must be victoriametrics/victorialogs/tempo; got {sorted(uids)}",
    )


def validate_minio_overlay(documents: list[dict]) -> None:
    tempo_config = named(documents, "ConfigMap", "tempo-config")
    text = tempo_config.get("data", {}).get("tempo.yml", "")
    require("backend: s3" in text, "Tempo MinIO overlay must use S3 backend")
    require("bucket: observability-tempo" in text, "Tempo MinIO bucket must be observability-tempo")
    require("${TEMPO_S3_ACCESS_KEY}" in text, "Tempo MinIO access key must come from env expansion")
    require("${TEMPO_S3_SECRET_KEY}" in text, "Tempo MinIO secret key must come from env expansion")

    tempo = named(documents, "Deployment", "tempo")
    container = deployment_container(tempo, "tempo")
    env = {item.get("name"): item for item in container.get("env", [])}
    for variable in ("TEMPO_S3_ACCESS_KEY", "TEMPO_S3_SECRET_KEY"):
        require(variable in env, f"Tempo MinIO overlay missing {variable}")
        secret_ref = env[variable].get("valueFrom", {}).get("secretKeyRef", {})
        require(secret_ref.get("name") == "tempo-minio", f"{variable} must use Secret/tempo-minio")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rendered-dir",
        type=Path,
        default=Path(".ci/rendered"),
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    rendered = (root / args.rendered_dir).resolve() if not args.rendered_dir.is_absolute() else args.rendered_dir

    checks = [
        ("Taskfile", lambda: validate_taskfile(root)),
        ("backend", lambda: validate_backend(load_yaml_documents(rendered / "backend.yaml"))),
        ("console", lambda: validate_console(load_yaml_documents(rendered / "console.yaml"))),
        ("tempo-minio", lambda: validate_minio_overlay(load_yaml_documents(rendered / "backend-minio.yaml"))),
    ]

    failures: list[str] = []
    for label, check in checks:
        try:
            check()
            print(f"PASS {label}")
        except (CheckError, KeyError, TypeError, yaml.YAMLError) as exc:
            failures.append(f"{label}: {exc}")
            print(f"FAIL {label}: {exc}", file=sys.stderr)

    if failures:
        print(f"OCO CI validation failed: {len(failures)} check group(s)", file=sys.stderr)
        return 1

    print("OCO CI validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
