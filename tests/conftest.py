import sys
from pathlib import Path
from trace import PRAGMA_NOCOVER, Trace, _find_executable_linenos

import pytest


COVERAGE_THRESHOLD = 80.0
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"


def _executable_lines(file_path: Path) -> set[int]:
    executable = set(_find_executable_linenos(str(file_path)))
    if not executable:
        return set()

    try:
        source_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return executable

    return {
        lineno
        for lineno in executable
        if 0 <= lineno - 1 < len(source_lines)
        and PRAGMA_NOCOVER not in source_lines[lineno - 1]
    }


def _coverage_by_file(results: Trace) -> dict[Path, float]:
    counts = results.counts
    coverage_map: dict[Path, float] = {}

    for file_path in SRC_ROOT.rglob("*.py"):
        executable_lines = _executable_lines(file_path)
        if not executable_lines:
            continue

        executed_lines = {
            lineno
            for (filename, lineno), hits in counts.items()
            if Path(filename).resolve() == file_path.resolve() and hits > 0
        }
        coverage_map[file_path] = (len(executed_lines & executable_lines) / len(executable_lines)) * 100

    return coverage_map


def _calculate_coverage(results: Trace) -> tuple[float, dict[Path, float]]:
    coverage_map = _coverage_by_file(results)
    if not coverage_map:
        return 100.0, {}

    executable_totals = 0
    executed_totals = 0
    for file_path, percent in coverage_map.items():
        executable_lines = len(_executable_lines(file_path))
        executable_totals += executable_lines
        executed_totals += int(executable_lines * (percent / 100))

    overall = (executed_totals / executable_totals) * 100 if executable_totals else 100.0
    return overall, coverage_map


def pytest_sessionstart(session: pytest.Session) -> None:
    tracer = Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.exec_prefix])
    session.config._career_compass_tracer = tracer
    sys.settrace(tracer.globaltrace)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    tracer = getattr(session.config, "_career_compass_tracer", None)
    sys.settrace(None)

    if tracer is None:
        return

    results = tracer.results()
    coverage_percent, coverage_map = _calculate_coverage(results)
    session.config._career_compass_coverage = coverage_percent
    session.config._career_compass_file_coverage = coverage_map

    if coverage_percent < COVERAGE_THRESHOLD and exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminal_reporter:
            terminal_reporter.section("coverage summary")
            terminal_reporter.write_line(
                f"Total coverage across src/: {coverage_percent:.2f}%"
            )
            terminal_reporter.write_line(
                f"Coverage below required threshold of {COVERAGE_THRESHOLD:.0f}%"
            )


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    coverage_percent = getattr(config, "_career_compass_coverage", None)
    coverage_map = getattr(config, "_career_compass_file_coverage", {})

    if coverage_percent is None:
        return

    terminalreporter.section("coverage summary")
    terminalreporter.write_line(f"Total coverage across src/: {coverage_percent:.2f}%")
    terminalreporter.write_line(
        f"Required threshold: {COVERAGE_THRESHOLD:.0f}%"
    )

    if coverage_map:
        terminalreporter.write_sep("-", "File coverage breakdown")
        for file_path in sorted(coverage_map):
            terminalreporter.write_line(f"{file_path.relative_to(PROJECT_ROOT)}: {coverage_map[file_path]:.2f}%")
