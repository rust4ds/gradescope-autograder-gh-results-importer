import json
import os
import sys

import helpers
import lateness
import questions as questions_module
import repo_checks
import results as results_module

CONFIG_PATH = os.environ.get("AUTOGRADER_CONFIG") or os.path.join(os.path.dirname(__file__), "config.json")


def read_config(config_path):
    with open(config_path, "r") as f:
        return json.load(f)


def _grade_pass(config, clone_dir, grading_tmp_dir):
    """Run all questions + repo checks once. Returns (score, test_results, summaries)."""
    questions_module.setup_submission(config, clone_dir, grading_tmp_dir)

    test_results = []
    score = 0.0
    summaries = []

    for question in config["questions"]:
        fn_name = question.get("function", "")
        grade_fn = questions_module.GRADE_FUNCTIONS.get(fn_name, questions_module.grade_question)
        s, _max, results, msg = grade_fn(clone_dir, grading_tmp_dir, question)
        score += s
        test_results.extend(results)
        summaries.append(msg)
        print(msg)

    commit_score, commit_results = repo_checks.grade_commit_count(clone_dir, config)
    score += commit_score
    test_results.extend(commit_results)

    branch_score, branch_results = repo_checks.grade_branch_count(clone_dir, config)
    score += branch_score
    test_results.extend(branch_results)

    return score, test_results, summaries


def main():
    config = read_config(CONFIG_PATH)

    metadata_path = config["metadata_path"]
    grading_tmp_dir = config["grading_tmp_dir"]
    results_path = config["results_path"]

    try:
        clone_dir = helpers.resolve_student_repo(metadata_path, config)
    except Exception as e:
        _write_error(results_path, "Could not access student repo: {}".format(e))
        return

    # Grade the current state of the repo (this is what the student sees as their result).
    print("=== Grading current state ===")
    current_score, all_test_results, question_summaries = _grade_pass(
        config, clone_dir, grading_tmp_dir
    )
    demo_summary = questions_module.build_demo_run_summary(
        config, clone_dir, grading_tmp_dir
    )

    # If the submission is late and we have full git history, also grade the commit
    # at the deadline. The student's final score blends ontime + late at LATE_MULTIPLIER.
    late = lateness.is_late(metadata_path)
    ontime_score = None
    ontime_note = ""
    is_real_clone = clone_dir == config["clone_dir"]  # vs shallow GRADESCOPE_SUBMISSION_DIR

    if late and is_real_clone:
        due_date = lateness.get_due_date_from_path(metadata_path)
        if due_date is not None:
            ontime_commit = helpers.find_commit_before(clone_dir, due_date)
            if ontime_commit:
                original_ref = helpers.current_ref(clone_dir)
                try:
                    helpers.checkout(clone_dir, ontime_commit)
                    print("=== Grading code as of deadline ({}) ===".format(ontime_commit[:8]))
                    ontime_score, _, _ = _grade_pass(config, clone_dir, grading_tmp_dir)
                finally:
                    helpers.checkout(clone_dir, original_ref)
            else:
                ontime_score = 0.0
                ontime_note = "No commits before deadline — on-time score = 0."
                print(ontime_note)
    elif late and not is_real_clone:
        ontime_note = (
            "Late, but no full git clone available — falling back to current score "
            "with flat penalty."
        )
        print(ontime_note)

    final_score = lateness.apply_penalty(current_score, ontime_score, late)
    penalty_desc = lateness.describe(current_score, ontime_score, final_score, late)
    print(penalty_desc)

    summary_lines = question_summaries + [penalty_desc]
    if ontime_note:
        summary_lines.append(ontime_note)
    if demo_summary:
        summary_lines.extend(["", demo_summary])
    summary = "\n".join(summary_lines)

    results_module.write_results(final_score, all_test_results, summary, results_path)
    print("Results written to", results_path)
    print("Final score: {:.2f}".format(final_score))


def _write_error(results_path, message):
    """Write a 0-score error result so Gradescope always gets valid JSON."""
    print("ERROR:", message, file=sys.stderr)
    results_module.write_results(0.0, [], message, results_path)


if __name__ == "__main__":
    main()
