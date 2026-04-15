import json
import os
import sys

import helpers
import lateness
import questions as questions_module
import repo_checks
import results as results_module

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def read_config(config_path):
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    config = read_config(CONFIG_PATH)

    metadata_path = config["metadata_path"]
    clone_dir = config["clone_dir"]
    grading_tmp_dir = config["grading_tmp_dir"]
    results_path = config["results_path"]

    # --- Clone student repo ---
    try:
        github_url = helpers.get_github_url(metadata_path)
    except (ValueError, FileNotFoundError, KeyError) as e:
        _write_error(results_path, "Could not retrieve GitHub URL: {}".format(e))
        return

    print("Cloning {} ...".format(github_url))
    helpers.clone_git_repo(github_url, config["submission_branch"], clone_dir)

    # --- Set up grading directory (copy template + private tests) ---
    questions_module.setup_submission(config, clone_dir, grading_tmp_dir)

    # --- Grade each question ---
    all_test_results = []
    total_score = 0.0
    question_summaries = []

    for question in config["questions"]:
        fn_name = question["function"]
        grade_fn = questions_module.GRADE_FUNCTIONS.get(fn_name)
        if grade_fn is None:
            print("WARNING: no grade function '{}' found, skipping.".format(fn_name))
            continue

        score, max_score, test_results, msg = grade_fn(
            clone_dir, grading_tmp_dir, question
        )
        total_score += score
        all_test_results.extend(test_results)
        question_summaries.append(msg)
        print(msg)

    # --- Commit and branch checks ---
    commit_score, commit_results = repo_checks.grade_commit_count(clone_dir, config)
    total_score += commit_score
    all_test_results.extend(commit_results)

    branch_score, branch_results = repo_checks.grade_branch_count(clone_dir, config)
    total_score += branch_score
    all_test_results.extend(branch_results)

    # --- Apply lateness penalty ---
    final_score = lateness.compute_penalty(total_score, metadata_path)
    penalty_desc = lateness.describe_penalty(total_score, final_score, metadata_path)
    print(penalty_desc)

    # --- Build overall summary ---
    summary_lines = question_summaries + [penalty_desc]
    summary = "\n".join(summary_lines)

    # --- Write results ---
    results_module.write_results(final_score, all_test_results, summary, results_path)
    print("Results written to", results_path)
    print("Final score: {:.2f}".format(final_score))


def _write_error(results_path, message):
    """Write a 0-score error result so Gradescope always gets valid JSON."""
    print("ERROR:", message, file=sys.stderr)
    results_module.write_results(0.0, [], message, results_path)


if __name__ == "__main__":
    main()
