"""Offline mutation fixtures; runnable with unittest without importing the API."""

from __future__ import annotations

import copy
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from scripts import check_minilm_workflow as policy  # noqa: E402


class PublicationPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = policy.load_workflow()

    def reject(self, workflow: dict, message: str) -> None:
        with self.assertRaisesRegex(policy.PolicyError, message):
            policy.validate_policy(workflow)

    def test_current_workflow(self) -> None:
        self.assertEqual(len(policy.validate_policy(self.workflow)), 4)

    def test_untrusted_event_fixtures(self) -> None:
        for event in ("pull_request", "pull_request_target", "push", "workflow_call"):
            with self.subTest(event=event):
                bad = copy.deepcopy(self.workflow)
                bad["on"][event] = None
                self.reject(bad, "Manual dispatch only")

    def test_untrusted_guard_fixtures(self) -> None:
        # Each weak guard would admit a PR, an arbitrary branch, or a fork.
        for guard in (
            policy.GUARD.replace("workflow_dispatch", "pull_request"),
            policy.GUARD.replace("refs/heads/main", "refs/heads/feature"),
            policy.GUARD.replace("pecel-lelele/adept", "fork-owner/adept"),
            " && ".join(policy.GUARD.split(" && ")[1:]),
            " && ".join(policy.GUARD.split(" && ")[::2]),
            " && ".join(policy.GUARD.split(" && ")[:2]),
            policy.GUARD.replace(" && ", " || "),
            True,
        ):
            with self.subTest(guard=guard):
                bad = copy.deepcopy(self.workflow)
                bad["jobs"]["publish"]["if"] = guard
                self.reject(bad, "manual/main/source-repository guard")

    def test_expanded_permissions(self) -> None:
        for location in ("workflow", "job"):
            for permission in ("contents", "id-token", "actions"):
                with self.subTest(location=location, permission=permission):
                    bad = copy.deepcopy(self.workflow)
                    target = bad if location == "workflow" else bad["jobs"]["publish"]
                    target["permissions"][permission] = "write"
                    self.reject(bad, "[Pp]ermissions")

    def test_action_reference_fixtures(self) -> None:
        for index in range(4):
            for ref in ("v4", "abc123", "g" * 40):
                with self.subTest(index=index, ref=ref):
                    bad = copy.deepcopy(self.workflow)
                    bad["jobs"]["publish"]["steps"][index]["uses"] = (
                        policy.ACTIONS[index] + "@" + ref
                    )
                    self.reject(bad, "40-character commit SHA")
        bad = copy.deepcopy(self.workflow)
        bad["jobs"]["publish"]["steps"][0]["uses"] = "untrusted/action@" + "a" * 40
        self.reject(bad, "40-character commit SHA")

    def test_checkout_credentials(self) -> None:
        for inputs in ({}, {"persist-credentials": True}, {"persist-credentials": "false"}):
            with self.subTest(inputs=inputs):
                bad = copy.deepcopy(self.workflow)
                bad["jobs"]["publish"]["steps"][0]["with"] = inputs
                self.reject(bad, "credentials must not persist")

    def test_build_input_fixtures(self) -> None:
        for key, value, message in (
            ("context", "./src", "repository root"),
            ("file", "Dockerfile", "existing MiniLM Dockerfile"),
            ("platforms", "linux/arm64", "linux/amd64"),
            ("platforms", "linux/amd64,linux/arm64", "linux/amd64"),
            ("push", True, "Push must match"),
            ("push", "${{ github.ref == 'refs/heads/main' }}", "Push must match"),
            ("tags", "ghcr.io/other-owner/adept-minilm:latest", "Image tags"),
            ("tags", "ghcr.io/pecel-lelele/other-image:latest", "Image tags"),
            ("tags", policy.TAGS[0], "Image tags"),
            ("tags", "\n".join((*policy.TAGS, "ghcr.io/other/image:latest")), "Image tags"),
            ("secrets", "TOKEN=unexpected", "Unexpected build inputs"),
        ):
            with self.subTest(key=key, value=value):
                bad = copy.deepcopy(self.workflow)
                bad["jobs"]["publish"]["steps"][3]["with"][key] = value
                self.reject(bad, message)

    def test_dockerfile_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(policy.PolicyError, "Dockerfile must exist"):
                policy.validate_policy(self.workflow, Path(directory))

    def test_extra_execution_rejected(self) -> None:
        bad = copy.deepcopy(self.workflow)
        bad["jobs"]["publish"]["steps"].append({"run": "echo unsafe"})
        self.reject(bad, "Unexpected publish steps")
        bad = copy.deepcopy(self.workflow)
        bad["jobs"]["publish"]["steps"][0]["run"] = "echo unsafe"
        self.reject(bad, "Unexpected fields")

    def test_duplicate_yaml_keys_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text("permissions: {}\npermissions: write-all\n")
            with self.assertRaisesRegex(policy.PolicyError, "Duplicate YAML key"):
                policy.load_workflow(path)


class PublicActionTests(unittest.TestCase):
    ref = "actions/checkout@" + "a" * 40

    @patch.object(policy, "urlopen")
    def test_public_read_only_request(self, fetch) -> None:
        fetch.return_value = io.BytesIO(b"name: Checkout\nruns:\n  using: node24\n")
        policy.check_public_action(self.ref)
        request = fetch.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(
            request.full_url,
            f"https://raw.githubusercontent.com/actions/checkout/{'a' * 40}/action.yml",
        )
        self.assertEqual(dict(request.header_items()), {"User-agent": "adept-minilm-policy"})
        self.assertEqual(fetch.call_args.kwargs, {"timeout": 20})

    @patch.object(policy, "urlopen")
    def test_yaml_extension_fallback(self, fetch) -> None:
        fetch.side_effect = [
            HTTPError("url", 404, "Not found", {}, None),
            io.BytesIO(b"runs: {using: composite, steps: []}"),
        ]
        policy.check_public_action(self.ref)
        self.assertTrue(fetch.call_args.args[0].full_url.endswith("/action.yaml"))

    @patch.object(policy, "urlopen")
    def test_missing_action_is_failure(self, fetch) -> None:
        fetch.side_effect = HTTPError("url", 404, "Not found", {}, None)
        with self.assertRaisesRegex(policy.PolicyError, "No public action.*HTTP 404"):
            policy.check_public_action(self.ref)
        self.assertEqual(fetch.call_count, 2)

    @patch.object(policy, "urlopen")
    def test_network_failures_are_explicit(self, fetch) -> None:
        for error in (
            HTTPError("url", 403, "Forbidden", {}, None),
            HTTPError("url", 500, "Unavailable", {}, None),
            URLError("unreachable"),
            TimeoutError("timed out"),
        ):
            with self.subTest(error=error):
                fetch.side_effect = error
                with self.assertRaisesRegex(policy.PolicyError, "Cannot verify actions/checkout@"):
                    policy.check_public_action(self.ref)

    @patch.object(policy, "urlopen")
    def test_invalid_manifest(self, fetch) -> None:
        fetch.return_value = io.BytesIO(b"not-an-action")
        with self.assertRaisesRegex(policy.PolicyError, "Invalid action manifest"):
            policy.check_public_action(self.ref)

    @patch.object(policy, "urlopen")
    def test_arbitrary_url_rejected_before_network(self, fetch) -> None:
        with self.assertRaisesRegex(policy.PolicyError, "Invalid public action reference"):
            policy.check_public_action("https://example.invalid/action")
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
