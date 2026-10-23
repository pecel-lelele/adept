"""Isolated quality-runner regressions: no tools, application imports or services."""

from __future__ import annotations

import importlib.util
import io
import itertools
import subprocess
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

DEV_PY = Path(__file__).resolve().parents[1] / "src/scripts/dev.py"
LABELS = ("ruff lint", "ruff format", "frontend lint")
COMMANDS = [
    ["test-python", "-m", "ruff", "check", "."],
    ["test-python", "-m", "ruff", "format", "--check", "."],
    ["test-pnpm", "lint"],
]


class LintRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location("dev_quality", DEV_PY)
        assert spec and spec.loader
        self.dev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.dev)
        patches = [
            patch.object(self.dev, "load_env"),
            patch.object(self.dev, "py", side_effect=lambda *args: ["test-python", *args]),
            patch.object(self.dev, "pnpm", return_value=["test-pnpm"]),
            patch.object(self.dev.subprocess, "run"),
            patch.object(
                self.dev.subprocess, "Popen", side_effect=AssertionError("unexpected server")
            ),
            patch.object(self.dev, "db_up", side_effect=AssertionError("unexpected database")),
            patch.object(
                self.dev, "task_db_migrate", side_effect=AssertionError("unexpected migration")
            ),
            patch.object(self.dev, "task_seed", side_effect=AssertionError("unexpected seed")),
        ]
        mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        self.commands = mocks[3]

    def command_results(self, codes: tuple[int, ...]) -> None:
        self.commands.reset_mock()
        self.commands.side_effect = [
            subprocess.CompletedProcess(command, code)
            for command, code in zip(COMMANDS, codes, strict=True)
        ]

    def assert_commands_once(self) -> None:
        self.assertEqual([call.args[0] for call in self.commands.call_args_list], COMMANDS)
        self.assertEqual(
            [call.kwargs["cwd"] for call in self.commands.call_args_list],
            [self.dev.ROOT, self.dev.ROOT, self.dev.WEB],
        )

    def test_every_failure_combination_runs_each_check_once_and_preserves_exit_status(self) -> None:
        for codes in itertools.product((0, 2), repeat=3):
            with self.subTest(codes=codes):
                self.command_results(codes)
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    result = self.dev.main(["lint"])
                self.assertEqual(result, int(any(codes)))
                self.assert_commands_once()
                failed = [label for label, code in zip(LABELS, codes, strict=True) if code]
                for label, code in zip(LABELS, codes, strict=True):
                    self.assertIn(f"lint: {label}", out.getvalue())
                    self.assertEqual(f"FAILED {label}:" in err.getvalue(), bool(code))
                if failed:
                    self.assertIn(f"make lint failed: {', '.join(failed)}", err.getvalue())
                    self.assertIn("command failed (2)", err.getvalue())
                else:
                    self.assertEqual(err.getvalue(), "")

    def test_task_lint_raises_only_after_reporting_all_failures(self) -> None:
        self.command_results((1, 2, 3))
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            with self.assertRaisesRegex(
                self.dev.TaskError, "make lint failed: ruff lint, ruff format, frontend lint"
            ):
                self.dev.task_lint()
        self.assert_commands_once()
        for label in LABELS:
            self.assertIn(f"FAILED {label}:", err.getvalue())

    def test_python_command_preparation_failure_does_not_hide_frontend_lint(self) -> None:
        self.dev.py.side_effect = self.dev.TaskError("Python environment unavailable")
        self.commands.return_value = subprocess.CompletedProcess(COMMANDS[2], 0)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(self.dev.main(["lint"]), 1)
        self.assertEqual(self.dev.py.call_count, 2)
        self.assertEqual([call.args[0] for call in self.commands.call_args_list], [COMMANDS[2]])

    def test_make_check_continues_other_stages_after_aggregated_lint_failure(self) -> None:
        self.command_results((1, 1, 1))
        stages = [
            "task_i18n_check",
            "task_test",
            "task_typecheck",
            "task_contracts_check",
        ]
        callbacks = []
        for name in stages:
            callback = Mock()
            callbacks.append(callback)
            patcher = patch.object(self.dev, name, callback)
            patcher.start()
            self.addCleanup(patcher.stop)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(self.dev.main(["check"]), 1)
        self.assert_commands_once()
        for callback in callbacks:
            callback.assert_called_once_with()
        self.assertIn(
            "FAILED lint: make lint failed: ruff lint, ruff format, frontend lint", err.getvalue()
        )
        self.assertIn("make check failed: lint", err.getvalue())

    def test_make_check_reports_all_combinations_of_multiple_non_lint_failures(self) -> None:
        stage_names = ["i18n", "test", "typecheck", "contracts"]
        callbacks_by_stage = {
            "i18n": "task_i18n_check",
            "test": "task_test",
            "typecheck": "task_typecheck",
            "contracts": "task_contracts_check",
        }
        for failures in itertools.chain.from_iterable(
            itertools.combinations(stage_names, count) for count in range(2, len(stage_names) + 1)
        ):
            with self.subTest(failures=failures):
                self.command_results((0, 0, 0))
                callbacks = {}
                with ExitStack() as patches:
                    for stage, callback_name in callbacks_by_stage.items():
                        callback = Mock(
                            side_effect=(
                                self.dev.TaskError(f"{stage} failure")
                                if stage in failures
                                else None
                            )
                        )
                        callbacks[stage] = callback
                        patches.enter_context(patch.object(self.dev, callback_name, callback))

                    err = io.StringIO()
                    with redirect_stdout(io.StringIO()), redirect_stderr(err):
                        self.assertEqual(self.dev.main(["check"]), 1)

                    self.assert_commands_once()
                    for stage, callback in callbacks.items():
                        callback.assert_called_once_with()
                        self.assertEqual(
                            f"FAILED {stage}: {stage} failure" in err.getvalue(),
                            stage in failures,
                        )
                    self.assertIn(f"make check failed: {', '.join(failures)}", err.getvalue())


if __name__ == "__main__":
    unittest.main()
