import os
import subprocess

import helpers
import results as results_module


def setup_submission(config, student_repo_dir, grading_tmp_dir):
    """
    Prepare the grading directory from the private rust_template.

    Copies the full template (with our tests.rs files) into grading_tmp_dir.
    Student mod.rs files are injected per-question by grade_question.
    """
    helpers.setup_grading_dir(config["rust_template_dir"], grading_tmp_dir)


def grade_question(student_repo_dir, grading_tmp_dir, question):
    """
    Grade a single question using cargo test.

    1. Copy student's mod.rs into the grading dir.
    2. Run cargo test with the question's filter.
    3. Count passing tests by name.
    4. Build Gradescope test results with io/structural visibility.
    Returns (score, max_score, test_results, summary_message).
    """
    question_name = question["name"]
    test_configs = question["tests"]
    max_score = question["points"]

    try:
        helpers.copy_student_module(student_repo_dir, grading_tmp_dir, question_name)
    except FileNotFoundError as e:
        zero_results = [
            results_module.make_question_test_result(
                question["display_name"], t, False
            )
            for t in test_configs
        ]
        msg = "No submission for {}: {}".format(question_name, e)
        return (0.0, float(max_score), zero_results, msg)

    try:
        cargo_output = helpers.run_cargo_tests(
            grading_tmp_dir, question["cargo_test_filter"]
        )
    except subprocess.TimeoutExpired:
        zero_results = [
            results_module.make_question_test_result(
                question["display_name"], t, False
            )
            for t in test_configs
        ]
        msg = "{}: timed out after {}s — possible infinite loop".format(
            question["display_name"], helpers.CARGO_TEST_TIMEOUT
        )
        return (0.0, float(max_score), zero_results, msg)

    test_names = [t["name"] for t in test_configs]
    passing = helpers.count_passing_by_name(cargo_output, test_names)

    score = 0.0
    test_results = []
    for t in test_configs:
        passed = passing[t["name"]]
        if passed:
            score += t["points"]
        test_results.append(
            results_module.make_question_test_result(
                question["display_name"], t, passed
            )
        )

    passed_count = sum(1 for v in passing.values() if v)
    total_count = len(test_configs)
    msg = "{}: {}/{} tests passed ({:.1f}/{} points)".format(
        question["display_name"], passed_count, total_count, score, max_score
    )
    return (score, float(max_score), test_results, msg)


def grade_run_output(student_repo_dir, grading_tmp_dir, question):
    """
    Grade by running `cargo run` and matching each check's line_prefix against expected output.
    """
    question_name = question["question_module"]
    checks = question["checks"]
    max_score = question["points"]
    display = question["display_name"]

    try:
        helpers.copy_student_module(student_repo_dir, grading_tmp_dir, question_name)
    except FileNotFoundError as e:
        zero_results = [_make_run_result(display, c, False, "No submission") for c in checks]
        return (0.0, float(max_score), zero_results, "No submission for {}: {}".format(question_name, e))

    try:
        actual_output = helpers.run_cargo_binary(grading_tmp_dir)
    except subprocess.TimeoutExpired:
        zero_results = [_make_run_result(display, c, False, "Timed out") for c in checks]
        msg = "{}: cargo run timed out after {}s".format(display, helpers.CARGO_TEST_TIMEOUT)
        return (0.0, float(max_score), zero_results, msg)

    # Parse output into {prefix: value} pairs
    parsed = _parse_output_lines(actual_output)

    score = 0.0
    test_results = []
    for c in checks:
        prefix = c["line_prefix"]
        expected = c["expected"]
        actual = parsed.get(prefix)

        if actual is None:
            passed = False
            detail = "Line '{}' not found in output".format(prefix)
        elif actual.strip() == expected.strip():
            passed = True
            detail = actual.strip()
        else:
            passed = False
            detail = "got: {}  expected: {}".format(actual.strip(), expected.strip())

        if passed:
            score += c["points"]
        test_results.append(_make_run_result(display, c, passed, detail))

    passed_count = sum(1 for r in test_results if r["score"] > 0)
    msg = "{}: {}/{} output checks passed ({:.1f}/{} points)".format(
        display, passed_count, len(checks), score, max_score
    )
    return (score, float(max_score), test_results, msg)


def _parse_output_lines(output):
    """Parse 'Key: value' lines into {key+':': value}. Key format matches line_prefix config fields."""
    result = {}
    for line in output.splitlines():
        if ": " in line:
            prefix, _, value = line.partition(": ")
            result[prefix.strip() + ":"] = value
    return result


def _make_run_result(display_name, check, passed, detail):
    score = check["points"] if passed else 0.0
    name = "{} - {}".format(display_name, check["name"])
    desc = check.get("description", check["name"])
    output = "PASS: {}".format(desc) if passed else "FAIL: {} ({})".format(desc, detail)
    return results_module.make_test_result(name, score, check["points"], output, "visible")


def build_demo_run_summary(config, student_repo_dir, grading_tmp_dir):
    """
    Optionally run `cargo run` and return a text block for the Gradescope summary.
    Controlled by config["demo_run_summary"].
    """
    demo_cfg = config.get("demo_run_summary", {})
    if not demo_cfg.get("enabled", False):
        return ""

    question_module = demo_cfg.get("question_module")
    if not question_module:
        return ""

    title = demo_cfg.get("title", "Cargo run demo output")
    max_chars = int(demo_cfg.get("max_chars", 4000))
    timeout_seconds = int(demo_cfg.get("timeout_seconds", 12))
    run_in_student_repo = demo_cfg.get("run_in_student_repo", True)

    try:
        run_dir = student_repo_dir
        if not run_in_student_repo:
            helpers.setup_grading_dir(config["rust_template_dir"], grading_tmp_dir)
            helpers.copy_student_module(student_repo_dir, grading_tmp_dir, question_module)
            run_dir = grading_tmp_dir

        if not os.path.exists(os.path.join(run_dir, "Cargo.toml")):
            return "{}:\nUnavailable: no Cargo.toml found in {}".format(title, run_dir)

        # Keep demo output best-effort so it cannot stall grading completion.
        result = subprocess.run(
            ["cargo", "run"],
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
        )
        output = result.stdout.strip()
        if not output:
            output = "(no stdout)"
    except FileNotFoundError as e:
        return "{}:\nUnavailable: {}".format(title, e)
    except subprocess.TimeoutExpired:
        return "{}:\nTimed out after {}s (skipped in summary)".format(
            title, timeout_seconds
        )
    except Exception as e:
        return "{}:\nError while running cargo run: {}".format(title, e)

    if max_chars > 0 and len(output) > max_chars:
        output = output[:max_chars].rstrip() + "\n... [truncated]"

    return "{}:\n{}".format(title, output)


# Add entries here only for questions that need non-standard grading logic.
GRADE_FUNCTIONS = {
    "grade_run_output": grade_run_output,
}
