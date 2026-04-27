import csv
import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request


GRADESCOPE_SUBMISSION_DIR = "/autograder/submission"


def _redact_url(url):
    """Strip embedded credentials from a URL so it's safe to log."""
    return re.sub(r"https://[^@]+@", "https://", url)


def _authed_url(org, repo_name, token):
    return "https://{}@github.com/{}/{}.git".format(token, org, repo_name)


def _lower_str(value):
    """Safely lowercase possibly-null values from APIs/metadata."""
    return str(value or "").lower()


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
            student_name = metadata.get("users", [{}])[0].get("name")
            github_url = (
                config.get("debug_repo_url")
                or _get_intercepted_url()
                or _find_github_url_in_metadata(metadata)
                or _find_repo_via_classroom_api(student_email, student_name, config)
                or _find_repo_via_roster_csv(student_email, config)
                or _find_repo_via_api(student_email, config)
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
    print("Cloning {} ...".format(_redact_url(github_url)))
    _clone_git_repo(github_url, config["submission_branch"], clone_dir)
    return clone_dir


def _github_api(path, token, timeout=30):
    """Make an authenticated GitHub API GET request. Returns parsed JSON or None."""
    req = urllib.request.Request(
        "https://api.github.com{}".format(path),
        headers={
            "Authorization": "token {}".format(token),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print("GitHub API error ({}): {}".format(path, e))
        return None


def _find_repo_via_roster_csv(student_email, config):
    """
    Look up the student's GitHub username from a Classroom roster CSV
    (downloaded from GitHub Classroom: Students → Download).

    Each CSV row has columns: identifier, github_username, github_id, name.
    The identifier field contains the student's BU email (alongside their name).
    Returns an authenticated clone URL, or None if not found.
    """
    csv_path = config.get("roster_csv_path", "/autograder/source/roster.csv")
    org = config.get("github_org")
    prefix = config.get("repo_prefix", "")
    token = config.get("github_token")

    if not all([org, prefix, token, student_email]) or not os.path.exists(csv_path):
        return None

    needle = student_email.lower()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            identifier = (row.get("identifier") or "").lower()
            username = (row.get("github_username") or "").strip()
            if username and needle in identifier:
                return _find_repo_for_username(username, config, "roster CSV")

    return None


def _find_repo_via_classroom_api(student_email, student_name, config):
    """
    Find the student's repo via the GitHub Classroom API.
    Tries in order: roster_identifier == email, students.name == name (case-insensitive),
    then per-user public email lookup. Returns an authenticated clone URL, or None.
    """
    token = config.get("github_token")
    classroom_id = config.get("github_classroom_id")
    prefix = config.get("repo_prefix", "").rstrip("-")

    if not all([token, classroom_id]):
        return None

    assignments = _github_api("/classrooms/{}/assignments".format(classroom_id), token)
    if not assignments:
        return None

    assignment_id = None
    for a in assignments:
        if prefix and prefix in a.get("slug", ""):
            assignment_id = a["id"]
            break
    if not assignment_id:
        print("Classroom API: no assignment found matching prefix '{}'".format(prefix))
        return None

    norm_name = (student_name or "").strip().lower()

    # Collect every entry across all pages so we can fall back to email lookup if name fails
    all_entries = []
    page = 1
    while True:
        entries = _github_api(
            "/assignments/{}/accepted_assignments?per_page=100&page={}".format(assignment_id, page),
            token,
        )
        if not entries:
            break
        all_entries.extend(entries)

        # Pass 1: match on roster_identifier (only present if classroom has a CSV roster)
        for entry in entries:
            if student_email and entry.get("roster_identifier") == student_email:
                return _classroom_authed_url(entry, token, "roster_identifier")

        # Pass 2: match on student name (case-insensitive exact)
        if norm_name:
            for entry in entries:
                for student in entry.get("students", []):
                    if (student.get("name") or "").strip().lower() == norm_name:
                        return _classroom_authed_url(entry, token, "name")

        if len(entries) < 100:
            break
        page += 1

    # Pass 3: per-user public email lookup on each candidate's GitHub login
    if student_email:
        for entry in all_entries:
            for student in entry.get("students", []):
                login = student.get("login")
                if not login:
                    continue
                user = _github_api("/users/{}".format(login), token)
                if user and _lower_str(user.get("email")) == _lower_str(student_email):
                    return _classroom_authed_url(entry, token, "public email")

    print("Classroom API: no match for email={!r} name={!r}".format(student_email, student_name))
    return None


def _classroom_authed_url(entry, token, matched_by):
    full_name = entry.get("repository", {}).get("full_name")
    if not full_name:
        return None
    print("Found repo via Classroom API ({}): {}".format(matched_by, full_name))
    return "https://{}@github.com/{}.git".format(token, full_name)


def _repo_name_suffix(repo_name, expected_base):
    """
    Return numeric suffix for names like "<expected_base>-3", or 0 for exact match.
    Returns -1 for non-matches.
    """
    if repo_name == expected_base:
        return 0
    prefix = expected_base + "-"
    if repo_name.startswith(prefix):
        suffix = repo_name[len(prefix):]
        if suffix.isdigit():
            return int(suffix)
    return -1


def _list_org_repos(token, org):
    """
    Return all repos in the org (up to API pagination limits).
    """
    repos = []
    page = 1
    while True:
        batch = _github_api("/orgs/{}/repos?per_page=100&page={}".format(org, page), token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def _find_repo_for_username(username, config, source_label):
    """
    Resolve a student's assignment repo from username with suffix-aware matching.
    Supports repos like "<prefix><username>", "<prefix><username>-2", "<prefix><username>-3", etc.
    """
    token = config.get("github_token")
    org = config.get("github_org")
    prefix = config.get("repo_prefix", "")

    if not all([token, org, prefix, username]):
        return None

    expected_base = "{}{}".format(prefix, username)
    regex = re.compile(r"^{}(?:-\d+)?$".format(re.escape(expected_base)))
    repos = _list_org_repos(token, org)

    if repos:
        candidates = []
        for repo in repos:
            repo_name = repo.get("name", "")
            if not regex.match(repo_name):
                continue
            candidates.append(repo)

        if candidates:
            # Prefer most recently pushed; tie-break with largest numeric suffix.
            candidates.sort(
                key=lambda r: (
                    r.get("pushed_at") or "",
                    _repo_name_suffix(r.get("name", ""), expected_base),
                ),
                reverse=True,
            )
            chosen = candidates[0]["name"]
            print(
                "Found repo via {} (suffix-aware): {}/{}".format(
                    source_label, org, chosen
                )
            )
            return _authed_url(org, chosen, token)

    # Last-resort fallback for older behavior if list calls fail/unavailable.
    print("Falling back to inferred repo name via {}: {}/{}".format(source_label, org, expected_base))
    return _authed_url(org, expected_base, token)


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

    # Strategy 1: find GitHub username by email
    data = _github_api(
        "/search/users?q={}+in:email".format(urllib.parse.quote(student_email)),
        token,
    )
    if data and data.get("items"):
        username = data["items"][0]["login"]
        return _find_repo_for_username(username, config, "email search")

    # Strategy 2: scan org repos for one where student has commits
    print("Email search found no user — scanning org repos for {}".format(student_email))
    repos = _list_org_repos(token, org)
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
            return _authed_url(org, repo["name"], token)

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


def _find_github_url_in_metadata(metadata):
    """
    Check common metadata fields for a GitHub URL set by Gradescope.
    Handles retroactive regrading where the submitter is the instructor,
    not the student — in that case email lookup fails but Gradescope may
    still record the repo URL in the metadata.
    Returns the URL string, or None if not found.
    """
    candidates = [
        metadata.get("github_url"),
        metadata.get("url"),
        metadata.get("submission", {}).get("github_url"),
        metadata.get("submission", {}).get("url"),
    ]
    for url in candidates:
        if url and isinstance(url, str) and "github.com" in url:
            print("Found repo URL in submission metadata: {}".format(_redact_url(url)))
            return url.strip()
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
    result = subprocess.run(
        ["git", "checkout", branch], cwd=directory, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            "git checkout '{}' failed: {}".format(branch, result.stderr.strip())
        )


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


def find_commit_before(repo_dir, deadline):
    """
    Return the SHA of the most recent commit on HEAD's history with author/commit date
    on or before `deadline` (a timezone-aware datetime). None if no such commit exists.
    """
    cutoff = deadline.isoformat()
    result = subprocess.run(
        ["git", "rev-list", "-n", "1", "--first-parent", "--before", cutoff, "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip()
    return sha if sha else None


def current_ref(repo_dir):
    """Return the current branch name, or the SHA if detached."""
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "-q", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True,
    ).stdout.strip()
    if branch:
        return branch
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True,
    ).stdout.strip()


def checkout(repo_dir, ref):
    """Checkout the given ref (branch or SHA). Raises on failure."""
    subprocess.run(
        ["git", "checkout", "--quiet", ref],
        cwd=repo_dir, capture_output=True, text=True, check=True,
    )


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
