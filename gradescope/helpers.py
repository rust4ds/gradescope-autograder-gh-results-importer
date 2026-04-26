import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request


GRADESCOPE_SUBMISSION_DIR = "/autograder/submission"


def resolve_student_repo(metadata_path, config):
    """
    Return the path to the student's repo, cloning only when necessary.

    When submission_method is "GitHub", Gradescope has already cloned the repo
    into /autograder/submission — use it directly.
    Otherwise, find the GitHub URL in the metadata and clone it.
    """
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)
        if metadata.get("submission_method") == "GitHub":
            clone_dir = config["clone_dir"]
            student_email = metadata.get("users", [{}])[0].get("email")
            github_url = (
                config.get("debug_repo_url")
                or _find_repo_via_api(student_email, config)
                or _get_intercepted_url()
                or _find_github_url_in_submission(GRADESCOPE_SUBMISSION_DIR)
            )
            if github_url:
                print("Cloning for full git history ...")
                _clone_git_repo(github_url, config["submission_branch"], clone_dir)
                return clone_dir
            else:
                print(
                    "WARNING: No GitHub URL found — using submission dir directly. "
                    "Commit/branch counts will not be available."
                )
                return GRADESCOPE_SUBMISSION_DIR

    # URL-based submission: find and clone the repo
    github_url = _get_github_url(metadata_path)
    clone_dir = config["clone_dir"]
    print("Cloning {} ...".format(github_url))
    _clone_git_repo(github_url, config["submission_branch"], clone_dir)
    return clone_dir


def _github_api(path, token):
    """Make an authenticated GitHub API GET request. Returns parsed JSON or None."""
    req = urllib.request.Request(
        "https://api.github.com{}".format(path),
        headers={
            "Authorization": "token {}".format(token),
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print("GitHub API error ({}): {}".format(path, e))
        return None


def _find_repo_via_api(student_email, config):
    """
    Use the GitHub API to find the student's repo URL given their email.

    Strategy 1: search GitHub users by email → construct repo name from prefix + username.
    Strategy 2: list org repos matching prefix → find one where student has commits.
    Returns an authenticated clone URL, or None if not found.
    """
    token = config.get("github_token")
    org = config.get("github_org")
    prefix = config.get("repo_prefix")

    if not all([token, org, prefix, student_email]):
        return None

    def authed_url(org, repo, token):
        return "https://{}@github.com/{}/{}.git".format(token, org, repo)

    # Strategy 1: find GitHub username by email
    data = _github_api(
        "/search/users?q={}+in:email".format(urllib.parse.quote(student_email)),
        token,
    )
    if data and data.get("items"):
        username = data["items"][0]["login"]
        repo_name = "{}{}".format(prefix, username)
        print("Found repo via email search: {}/{}".format(org, repo_name))
        return authed_url(org, repo_name, token)

    # Strategy 2: scan org repos for one where student has commits
    print("Email search found no user — scanning org repos for {}".format(student_email))
    repos = _github_api("/orgs/{}/repos?per_page=100".format(org), token)
    if not repos:
        return None
    for repo in repos:
        if not repo["name"].startswith(prefix):
            continue
        commits = _github_api(
            "/repos/{}/{}/commits?author={}&per_page=1".format(
                org, repo["name"], urllib.parse.quote(student_email)
            ),
            token,
        )
        if commits:
            print("Found repo via commit scan: {}/{}".format(org, repo["name"]))
            return authed_url(org, repo["name"], token)

    return None


INTERCEPTED_URL_FILE = "/tmp/gradescope_repo_url.txt"


def _get_intercepted_url():
    """
    Read the GitHub URL captured by the git wrapper installed in setup.sh.
    Returns the URL string, or None if the wrapper didn't fire.
    """
    if os.path.exists(INTERCEPTED_URL_FILE):
        with open(INTERCEPTED_URL_FILE) as f:
            url = f.read().strip()
        if url:
            return url
    return None


def _find_github_url_in_submission(submission_dir):
    """
    Look for a GitHub URL in a plain-text file inside the submission directory.
    Returns the URL string, or None if not found.
    Gradescope strips .git so we can't read the remote from the clone itself —
    instead, instructors ask students to include a url.txt file in their submission.
    """
    for fname in os.listdir(submission_dir):
        fpath = os.path.join(submission_dir, fname)
        if os.path.isfile(fpath) and fname.endswith(".txt"):
            with open(fpath) as fh:
                content = fh.read().strip()
            if "github.com" in content:
                return content
    return None


def _clone_git_repo(repo, branch, directory):
    if "/tree/" in repo:
        repo = repo[: repo.index("/tree/")]
    if not repo.endswith(".git"):
        repo = repo + ".git"

    shutil.rmtree(directory, ignore_errors=True)
    subprocess.run(["git", "clone", repo, directory], capture_output=True, check=True)
    subprocess.run(["git", "checkout", branch], cwd=directory, capture_output=True)


def _get_github_url(metadata_path):
    """Extract the student's GitHub repo URL from submission metadata. Raises ValueError if absent."""
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    candidates = [
        metadata.get("github_url"),
        metadata.get("url"),
        metadata.get("submission", {}).get("github_url"),
        metadata.get("submission", {}).get("url"),
    ]
    for url in candidates:
        if url and isinstance(url, str) and "github.com" in url:
            return url.strip()

    raise ValueError(
        "No GitHub URL found in submission metadata. "
        "Metadata keys: {}".format(list(metadata.keys()))
    )


def setup_grading_dir(template_dir, grading_tmp_dir):
    shutil.rmtree(grading_tmp_dir, ignore_errors=True)
    shutil.copytree(template_dir, grading_tmp_dir)


def copy_student_module(student_repo_dir, grading_tmp_dir, question_name):
    """Copy the student's mod.rs into the grading directory. Raises FileNotFoundError if absent."""
    src = os.path.join(student_repo_dir, "src", question_name, "mod.rs")
    dst = os.path.join(grading_tmp_dir, "src", question_name, "mod.rs")

    if not os.path.exists(src):
        raise FileNotFoundError(
            "No submission found for {}: expected {}".format(question_name, src)
        )

    shutil.copy2(src, dst)


CARGO_TEST_TIMEOUT = 60  # guards against infinite loops in student code


def run_cargo_binary(grading_tmp_dir):
    """Run `cargo run` and return stdout. Does not raise on non-zero exit."""
    result = subprocess.run(
        ["cargo", "run"],
        cwd=grading_tmp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=CARGO_TEST_TIMEOUT,
    )
    return result.stdout


def run_cargo_tests(grading_tmp_dir, test_filter):
    """Run cargo test with the given filter and return combined stdout+stderr. Does not raise on non-zero exit."""
    result = subprocess.run(
        ["cargo", "test", test_filter, "--", "--test-threads=1"],
        cwd=grading_tmp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=CARGO_TEST_TIMEOUT,
    )
    return result.stdout


def count_passing_by_name(cargo_output, test_names):
    """Return {test_name: passed} for each name. Anchored match avoids test_foo matching test_foo_bar."""
    passing = {}
    for name in test_names:
        pattern = r"test (?:\S+::)*{} \.\.\. ok".format(re.escape(name))
        passing[name] = bool(re.search(pattern, cargo_output))
    return passing


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
