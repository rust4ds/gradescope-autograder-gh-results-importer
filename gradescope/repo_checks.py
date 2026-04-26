import helpers
import results as results_module


def _make_threshold_result(threshold, unit, passed, actual):
    """Build a Gradescope test result for a single commit/branch threshold."""
    points = threshold["points"]
    score = float(points) if passed else 0.0
    key = "min_commits" if unit == "commit" else "min_branches"
    required = threshold[key]
    name = threshold["name"]

    if passed:
        output = "PASS: {} {}s (required: {})".format(actual, unit, required)
    else:
        output = "FAIL: {} {}s (required: {})".format(actual, unit, required)

    return results_module.make_test_result(
        name, score, float(points), output, "visible"
    )


def grade_commit_count(repo_dir, config):
    """
    Grade commit count against configured thresholds.

    Awards points for each threshold met (partial credit by tier).
    Returns (total_score, test_results).
    """
    if "commit_count" not in config:
        return (0.0, [])

    actual = helpers.count_commits(repo_dir)
    score = 0.0
    test_results = []

    for threshold in config["commit_count"]["thresholds"]:
        passed = actual >= threshold["min_commits"]
        if passed:
            score += threshold["points"]
        test_results.append(_make_threshold_result(threshold, "commit", passed, actual))

    return (score, test_results)


def grade_branch_count(repo_dir, config):
    """
    Grade branch count against configured thresholds.

    Returns (total_score, test_results).
    """
    if "branch_count" not in config:
        return (0.0, [])

    actual = helpers.count_branches(repo_dir)
    score = 0.0
    test_results = []

    for threshold in config["branch_count"]["thresholds"]:
        passed = actual >= threshold["min_branches"]
        if passed:
            score += threshold["points"]
        test_results.append(_make_threshold_result(threshold, "branch", passed, actual))

    return (score, test_results)
