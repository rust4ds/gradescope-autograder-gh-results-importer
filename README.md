# Gradescope Rust Autograder

Gradescope autograder for Rust assignments. Students submit a GitHub Classroom repository; the autograder clones it, runs private `cargo test` suites against the student's implementation, checks commit/branch hygiene, applies a lateness penalty, and writes a Gradescope-compatible JSON results file.

## How it works

```
Gradescope submission
        │
        ▼
grader.py
  ├── helpers.resolve_student_repo()   — clone student repo (full history)
  ├── questions.setup_submission()     — copy private rust_template into /tmp
  ├── questions.grade_question()       — inject student mod.rs, run cargo test, score
  ├── repo_checks.grade_*_count()      — commit and branch count thresholds
  ├── lateness.compute_penalty()       — 50% late penalty formula
  └── results.write_results()          — write /autograder/results/results.json
```

The private test suite (`rust_template/src/qN/tests.rs`) is never given to students. At grade time, the student's `src/qN/mod.rs` is copied into the template so private tests run against their implementation.

## Repository layout

```
gradescope/
  grader.py           — entry point called by run_autograder
  helpers.py          — git cloning, cargo execution, test output parsing
  questions.py        — question graders; GRADE_FUNCTIONS override hook
  results.py          — Gradescope JSON result builders
  repo_checks.py      — commit/branch count grading
  lateness.py         — lateness penalty formula
  setup.sh            — environment setup (installs Rust, pre-warms Cargo)
  run_autograder      — called by Gradescope; runs grader.py
  make_zip.sh         — packages an assignment for upload to Gradescope
  _template/          — starter template for new assignments
    config.json
    rust_template/
    CHECKLIST.md      — step-by-step checklist for deploying a new assignment
  hw5/                — HW05 assignment config and private test suite
    config.json
    rust_template/
```

## Deploying a new assignment

See [`gradescope/_template/CHECKLIST.md`](gradescope/_template/CHECKLIST.md) for the full step-by-step process. The short version:

1. Copy `gradescope/_template` to `gradescope/hwNN`
2. Update `config.json` with point values, thresholds, questions, `github_token`, `github_org`, and `repo_prefix` (see Config reference below for required token scopes)
3. Write private tests in `rust_template/src/qN/tests.rs`; stubs in `mod.rs`
4. Point `setup.sh`'s pre-warm build at the new template
5. Run `./make_zip.sh hwNN` to produce `hwNN_autograder.zip`
6. Upload to **Gradescope → Assignment → Configure Autograder**

## Config reference

| Field | Description |
|---|---|
| `assignment_name` | Identifier used in log output |
| `submission_branch` | Branch checked out from student repo (usually `main`) |
| `rust_template_dir` | Absolute path to private template on Gradescope server |
| `grading_tmp_dir` | Scratch directory for grading (wiped each run) |
| `clone_dir` | Where the student repo is cloned |
| `metadata_path` | Injected by Gradescope; do not change |
| `results_path` | Read by Gradescope; do not change |
| `github_token` | PAT used to clone private student repos and call the GitHub API |
| `github_org` | GitHub org where student repos live (used by API repo search) |
| `repo_prefix` | Prefix for student repo names (e.g. `hw5-distance-metrics-`) |
| `debug_repo_url` | Override: clone this URL instead of looking up the student's repo |
| `commit_count.thresholds` | Array of `{name, min_commits, points, description}` tiers |
| `branch_count.thresholds` | Array of `{name, min_branches, points, description}` tiers |
| `questions[].name` | Must match `src/qN/` directory in both repos |
| `questions[].cargo_test_filter` | Passed to `cargo test <filter>` — usually `qN::tests::` |
| `questions[].tests[].kind` | `"io"` = visible to students; `"structural"` = hidden until after due date |
| `questions[].function` | Omit for standard cargo-test grading; set to use a custom grader |

### GitHub token permissions

The token needs **Contents: Read** and **Metadata: Read** on student repos, plus **Members: Read** at the org level if using the API repo search (`github_org` + `repo_prefix`).

## Lateness penalty

Applied when `submission_time > due_date`:

```
final = best_ontime_score + 0.5 * (raw_score - best_ontime_score)
```

`best_ontime_score` is the highest score from any prior on-time submission for that student (0 if none). On-time submissions are returned unchanged. If `submission_metadata.json` is absent (local testing), the raw score is used with a warning.

## Custom question graders

To grade a question differently than the default `cargo test` pass/fail (This can be used similarly to the Cargo Demo of prior HW's): 

```python
# questions.py
def grade_my_question(student_repo_dir, grading_tmp_dir, question):
    ...
    return (score, max_score, test_results, summary_msg)

GRADE_FUNCTIONS = {
    "grade_my_question": grade_my_question,
}
```

Then set `"function": "grade_my_question"` in the question's config entry. See `grade_run_output` in `questions.py` for a working example (used for output-based grading).