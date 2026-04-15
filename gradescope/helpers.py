import json
import os
import re
import subprocess


# ---------------------------------------------------------------------------
# GitHub repo cloning (adapted from ds210-sp26-a1-hw/grader/helpers.py)
# ---------------------------------------------------------------------------

LAST_REPO = None


def clone_git_repo(repo, branch, directory):
    """Clone a git repo to the given directory. Skips re-cloning if same repo."""
    if "/tree/" in repo:
        repo = repo[: repo.index("/tree/")]
    if not repo.endswith(".git"):
        repo = repo + ".git"

    global LAST_REPO
    if repo != LAST_REPO:
        subprocess.run(["rm", "-rf", directory], capture_output=True)
        subprocess.run(["git", "clone", repo, directory], capture_output=True)

    subprocess.run(["git", "checkout", branch], cwd=directory, capture_output=True)
    LAST_REPO = repo


def get_github_url(metadata_path):
    """
    Extract the student's GitHub repo URL from Gradescope submission metadata.

    Gradescope places the submitted GitHub URL in the metadata under the
    'submission' key. Fallback: read a plain-text file from /autograder/submission/.
    """
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Primary: Gradescope GitHub submission type stores URL here
    submission = metadata.get("submission", {})
    url = submission.get("github_url") or submission.get("url")
    if url:
        return url.strip()

    # Fallback: text file in /autograder/submission/ (manual URL paste)
    submission_dir = os.path.dirname(metadata_path).replace(
        "submission_metadata.json", ""
    )
    submission_dir = "/autograder/submission"
    for fname in os.listdir(submission_dir):
        fpath = os.path.join(submission_dir, fname)
        if os.path.isfile(fpath):
            content = open(fpath).read().strip()
            if content.startswith("https://github.com") or content.startswith(
                "http://github.com"
            ):
                return content

    raise ValueError(
        "Could not find GitHub URL in submission metadata or submission directory."
    )


# ---------------------------------------------------------------------------
# Grading directory setup
# ---------------------------------------------------------------------------


def setup_grading_dir(template_dir, grading_tmp_dir):
    """Copy the rust template (with private tests) into a fresh grading directory."""
    subprocess.run(["rm", "-rf", grading_tmp_dir], capture_output=True)
    subprocess.run(["cp", "-r", template_dir, grading_tmp_dir], capture_output=True)


def copy_student_module(student_repo_dir, grading_tmp_dir, question_name):
    """
    Copy the student's mod.rs for a given question into the grading directory.

    Raises FileNotFoundError if the student did not submit the file.
    """
    src = os.path.join(student_repo_dir, "src", question_name, "mod.rs")
    dst = os.path.join(grading_tmp_dir, "src", question_name, "mod.rs")

    if not os.path.exists(src):
        raise FileNotFoundError(
            "No submission found for {}: expected {}".format(question_name, src)
        )

    subprocess.run(["cp", src, dst], check=True)


# ---------------------------------------------------------------------------
# Cargo test execution (adapted from ds210 helpers.py)
# ---------------------------------------------------------------------------


def run_cargo_tests(grading_tmp_dir, test_filter):
    """
    Run cargo test with the given filter and return combined stdout+stderr output.

    Does NOT raise on non-zero exit — failing tests are expected and normal.
    """
    result = subprocess.run(
        ["cargo", "test", test_filter, "--", "--test-threads=1"],
        cwd=grading_tmp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout


def count_passing_by_name(cargo_output, test_names):
    """
    For each test name, check whether 'test <name> ... ok' appears in cargo output.

    Returns a dict {test_name: True/False}.
    Matches on exact test name to avoid partial-name false positives.
    """
    passing = {}
    for name in test_names:
        # Anchor to word boundary so test_foo does not match test_foo_bar
        pattern = r"test (?:\S+::)*{} \.\.\. ok".format(re.escape(name))
        passing[name] = bool(re.search(pattern, cargo_output))
    return passing


# ---------------------------------------------------------------------------
# Git repository statistics
# ---------------------------------------------------------------------------


def count_commits(repo_dir):
    """Return the number of commits on HEAD in the given repo directory."""
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def count_branches(repo_dir):
    """Return the number of remote branches (excluding HEAD) in the repo."""
    result = subprocess.run(
        ["git", "branch", "-r"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    branches = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and "HEAD" not in line
    ]
    return len(branches)
