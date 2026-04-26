import json
import os


def make_test_result(name, score, max_score, output, visibility):
    return {
        "name": name,
        "score": score,
        "max_score": max_score,
        "output": output,
        "visibility": visibility,
    }


def make_question_test_result(question_name, test_config, passed):
    """Build a single Gradescope test result for a cargo test case."""
    score = test_config["points"] if passed else 0.0
    max_score = test_config["points"]
    name = "{} - {}".format(question_name, test_config["name"])
    kind = test_config.get("kind", "structural")

    if kind == "io":
        desc = test_config.get("description", test_config["name"])
        output = "PASS: {}".format(desc) if passed else "FAIL: expected {}".format(desc)
        visibility = "visible"
    else:
        output = "PASS" if passed else "FAIL"
        visibility = "after_due_date"

    return make_test_result(name, score, max_score, output, visibility)


def build_results(final_score, test_results, output_msg):
    return {
        "score": round(final_score, 2),
        "output": output_msg,
        "tests": test_results,
    }


def write_results(final_score, test_results, output_msg, results_path):
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    data = build_results(final_score, test_results, output_msg)
    with open(results_path, "w") as f:
        json.dump(data, f, indent=2)
