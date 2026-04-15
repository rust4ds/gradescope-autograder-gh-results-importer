import helpers
import results as results_module

# Set by grader.py before any grade function is called
SUBMISSION_DIR = None
GRADING_TMP_DIR = None


def setup_submission(config, student_repo_dir, grading_tmp_dir):
    """
    Prepare the grading directory from the private rust_template.

    Copies the full template (with our tests.rs files) into grading_tmp_dir.
    Student mod.rs files are injected per-question by each grade_q* function.
    """
    helpers.setup_grading_dir(config["rust_template_dir"], grading_tmp_dir)


def _grade_question(student_repo_dir, grading_tmp_dir, question):
    """
    Generic question grader used by grade_q1/q2/q3.

    1. Copy student's mod.rs into the grading dir.
    2. Run cargo test with the question's filter.
    3. Count passing tests by name.
    4. Build Gradescope test results with io/structural visibility.
    Returns (score, max_score, test_results, summary_message).
    """
    question_name = question["name"]
    test_configs = question["tests"]
    max_score = question["points"]

    # Attempt to copy student's implementation
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

    # Run tests
    cargo_output = helpers.run_cargo_tests(
        grading_tmp_dir, question["cargo_test_filter"]
    )

    # Check for compile error (no tests ran at all)
    test_names = [t["name"] for t in test_configs]
    passing = helpers.count_passing_by_name(cargo_output, test_names)

    # Accumulate score and build result objects
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


def grade_q1(student_repo_dir, grading_tmp_dir, question):
    return _grade_question(student_repo_dir, grading_tmp_dir, question)


def grade_q2(student_repo_dir, grading_tmp_dir, question):
    return _grade_question(student_repo_dir, grading_tmp_dir, question)


def grade_q3(student_repo_dir, grading_tmp_dir, question):
    return _grade_question(student_repo_dir, grading_tmp_dir, question)


# Map function name strings from config.json to callables
GRADE_FUNCTIONS = {
    "grade_q1": grade_q1,
    "grade_q2": grade_q2,
    "grade_q3": grade_q3,
}
