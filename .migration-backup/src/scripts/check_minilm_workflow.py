"""Fail-closed MiniLM publication policy. Never builds images or uses credentials.

Run with --check-actions in CI to also resolve public pinned action manifests.
Local policy tests are offline; this module needs only PyYAML, not the application.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/publish-minilm.yml"
GUARD = (
    "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main' "
    "&& github.repository == 'pecel-lelele/adept'"
)
DOCKERFILE = "src/pipelines/trends/runpod/Dockerfile"
ACTIONS = (
    "actions/checkout",
    "docker/setup-buildx-action",
    "docker/login-action",
    "docker/build-push-action",
)
TAGS = (
    "ghcr.io/pecel-lelele/adept-minilm:latest",
    "ghcr.io/pecel-lelele/adept-minilm:sha-${{ github.sha }}",
)


class PolicyError(ValueError):
    """An unsafe workflow or an unverifiable public action."""


class WorkflowLoader(yaml.SafeLoader):
    """Reject duplicate keys; use YAML 1.2-style booleans for GitHub's `on` key."""


# Do not mutate PyYAML's global resolver (other tests may use it).
WorkflowLoader.yaml_implicit_resolvers = {
    key: [(tag, regex) for tag, regex in values if tag != "tag:yaml.org,2002:bool"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$"), list("tf")
)


def unique_mapping(loader: WorkflowLoader, node: yaml.MappingNode) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise PolicyError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


WorkflowLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)


def load_workflow(path: Path = WORKFLOW) -> dict:
    with path.open() as stream:
        workflow = yaml.load(stream, Loader=WorkflowLoader)
    require(isinstance(workflow, dict), "Workflow must be a mapping")
    return workflow


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def validate_policy(workflow: dict, root: Path = ROOT) -> list[str]:
    """Allow only the reviewed publication shape; return public action references."""
    require(
        set(workflow) == {"name", "on", "permissions", "concurrency", "jobs"},
        "Unexpected workflow fields",
    )
    require(workflow["on"] == {"workflow_dispatch": None}, "Manual dispatch only")
    require(workflow["permissions"] == {"contents": "read"}, "Workflow permissions changed")
    require(
        workflow["concurrency"] == {"group": "publish-minilm-latest", "cancel-in-progress": False},
        "Publication concurrency changed",
    )
    require(set(workflow["jobs"]) == {"publish"}, "Only the publish job is allowed")
    job = workflow["jobs"]["publish"]
    require(
        set(job) == {"if", "runs-on", "timeout-minutes", "permissions", "steps"},
        "Unexpected publish job fields",
    )
    require(job["if"] == GUARD, "Job must require manual/main/source-repository guard")
    require(job["runs-on"] == "ubuntu-latest", "Use a GitHub-hosted Linux runner")
    require(job["timeout-minutes"] == 60, "Publication timeout changed")
    require(
        job["permissions"] == {"contents": "read", "packages": "write"},
        "Publish permissions must be only contents:read and packages:write",
    )
    steps = job["steps"]
    require(isinstance(steps, list) and len(steps) == len(ACTIONS), "Unexpected publish steps")
    refs = []
    for step, action in zip(steps, ACTIONS, strict=True):
        require(set(step) <= {"name", "uses", "with"}, f"Unexpected fields for {action}")
        ref = step.get("uses", "")
        require(
            isinstance(ref, str)
            and re.fullmatch(re.escape(action) + r"@[0-9a-f]{40}", ref) is not None,
            f"{action} must use a full 40-character commit SHA",
        )
        refs.append(ref)
    require(
        steps[0].get("with") == {"persist-credentials": False},
        "Checkout credentials must not persist, and checkout must use the approved commit",
    )
    require("with" not in steps[1], "Unexpected Buildx inputs")
    require(
        steps[2].get("with")
        == {
            "registry": "ghcr.io",
            "username": "${{ github.actor }}",
            "password": "${{ secrets.GITHUB_TOKEN }}",
        },
        "Login must use only the scoped GitHub token for GHCR",
    )
    build = steps[3].get("with", {})
    require(
        set(build) == {"context", "file", "platforms", "push", "tags", "labels"},
        "Unexpected build inputs",
    )
    require(build["context"] == ".", "Build context must be the repository root")
    require(
        build["file"] == DOCKERFILE and (root / DOCKERFILE).is_file(),
        "The existing MiniLM Dockerfile must exist at the approved path",
    )
    require(build["platforms"] == "linux/amd64", "Only linux/amd64 may be published")
    require(build["push"] == "${{ " + GUARD + " }}", "Push must match the trusted job guard")
    require(
        isinstance(build["tags"], str) and tuple(build["tags"].splitlines()) == TAGS,
        "Image tags must be exactly the MiniLM latest and commit tags",
    )
    require(
        build["labels"].splitlines()
        == [
            "org.opencontainers.image.source=https://github.com/${{ github.repository }}",
            "org.opencontainers.image.revision=${{ github.sha }}",
        ],
        "Image provenance labels changed",
    )
    return refs


def check_public_action(ref: str) -> None:
    """GET only public manifests at a pinned SHA. Fail clearly, including on outages."""
    require(
        re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", ref) is not None,
        f"Invalid public action reference: {ref}",
    )
    repository, sha = ref.split("@")
    for filename in ("action.yml", "action.yaml"):
        url = f"https://raw.githubusercontent.com/{repository}/{sha}/{filename}"
        request = Request(url, headers={"User-Agent": "adept-minilm-policy"})
        try:
            with urlopen(request, timeout=20) as response:  # no auth headers or secrets
                manifest = yaml.safe_load(response.read(1_000_000))
        except HTTPError as exc:
            if exc.code == 404:
                continue
            raise PolicyError(f"Cannot verify {ref}: HTTP {exc.code} at {url}") from exc
        except (URLError, TimeoutError, OSError, yaml.YAMLError) as exc:
            raise PolicyError(f"Cannot verify {ref} at {url}: {exc}") from exc
        require(
            isinstance(manifest, dict) and isinstance(manifest.get("runs"), dict),
            f"Invalid action manifest for {ref} at {url}",
        )
        return
    raise PolicyError(f"No public action.yml or action.yaml found for {ref} (HTTP 404)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-actions", action="store_true")
    args = parser.parse_args()
    try:
        refs = validate_policy(load_workflow())
        if args.check_actions:
            for ref in refs:
                check_public_action(ref)
                print(f"Verified public action: {ref}")
    except (PolicyError, yaml.YAMLError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, f"MiniLM workflow policy failed: {exc}\n")
    print("MiniLM publication policy passed (no build or publication performed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
