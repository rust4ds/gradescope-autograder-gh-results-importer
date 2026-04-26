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

    questions_module.setup_submission(config, clone_dir, grading_tmp_dir)

    all_test_results = []
    total_score = 0.0
    question_summaries = []

    for question in config["questions"]:
        fn_name = question.get("function", "")
        grade_fn = questions_module.GRADE_FUNCTIONS.get(fn_name, questions_module.grade_question)

        score, max_score, test_results, msg = grade_fn(
            clone_dir, grading_tmp_dir, question
        )
        total_score += score
        all_test_results.extend(test_results)
        question_summaries.append(msg)
        print(msg)

    commit_score, commit_results = repo_checks.grade_commit_count(clone_dir, config)
    total_score += commit_score
    all_test_results.extend(commit_results)

    branch_score, branch_results = repo_checks.grade_branch_count(clone_dir, config)
    total_score += branch_score
    all_test_results.extend(branch_results)

    final_score = lateness.compute_penalty(total_score, metadata_path)
    penalty_desc = lateness.describe_penalty(total_score, final_score, metadata_path)
    print(penalty_desc)

    summary = "\n".join(question_summaries + [penalty_desc])
    results_module.write_results(final_score, all_test_results, summary, results_path)
    print("Results written to", results_path)
    print("Final score: {:.2f}".format(final_score))


def _write_error(results_path, message):
    """Write a 0-score error result so Gradescope always gets valid JSON."""
    print("ERROR:", message, file=sys.stderr)
    results_module.write_results(0.0, [], message, results_path)


if __name__ == "__main__":
    main()
