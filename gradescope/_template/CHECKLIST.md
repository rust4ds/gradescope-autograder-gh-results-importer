# New Assignment Checklist

## 1. Copy the template

```bash
cp -r gradescope/_template gradescope/hwNN
```

## 2. Rename `hwNN` everywhere

- `config.json` — `assignment_name`, all four paths (`rust_template_dir`, `grading_tmp_dir`, `clone_dir`)
- `rust_template/Cargo.toml` — `name = "hwNN"`
- `rust_template/src/main.rs` — comment and println

## 3. Set point values and thresholds in `config.json`

- Adjust `commit_count` and `branch_count` thresholds and points to match the assignment rubric
- For each question: set `points`, `display_name`, `cargo_test_filter`

## 4. Add / remove questions

For each question `qN`:
- Add `rust_template/src/qN/mod.rs` and `rust_template/src/qN/tests.rs` (copy q1 as a starting point)
- Uncomment `mod qN;` in `rust_template/src/main.rs`
- Add the question block to `config.json`

## 5. Write the private tests (`tests.rs`)

- Each `#[test] fn` name must match a `"name"` entry in `config.json` exactly
- `kind: "io"` tests are visible to students immediately; write descriptive assertions
- `kind: "structural"` tests are hidden until after the due date; test edge cases

## 6. Write the stubs (`mod.rs`)

- Match the function signatures students will implement
- Body is exactly `unimplemented!()` — this file is given to students and replaced at grade time

## 7. Update `setup.sh`

Point the pre-warm build at the new template so Cargo dependencies are cached:

```bash
cargo build --manifest-path /autograder/source/gradescope/hwNN/rust_template/Cargo.toml
```

## 8. Verify locally

```bash
cd gradescope
# Edit config.json: set rust_template_dir to local path, remove metadata_path file
python3 grader.py
```

## Config field reference

| Field | Description |
|-------|-------------|
| `assignment_name` | Identifier used in log output |
| `submission_branch` | Branch to check out from student repo (usually `main`) |
| `rust_template_dir` | Absolute path to private template on Gradescope server |
| `grading_tmp_dir` | Scratch directory for grading (wiped each run) |
| `clone_dir` | Where the student repo is cloned |
| `metadata_path` | Gradescope injects this; don't change |
| `results_path` | Gradescope reads this; don't change |
| `commit_count.thresholds` | Each tier: `min_commits`, `points`, `name`, `description` |
| `branch_count.thresholds` | Each tier: `min_branches`, `points`, `name`, `description` |
| `questions[].name` | Must match `src/qN/` directory name |
| `questions[].cargo_test_filter` | Passed to `cargo test <filter>` — usually `qN::tests::` |
| `questions[].tests[].kind` | `"io"` = visible; `"structural"` = after_due_date |
| `questions[].function` | Omit for standard grading; set to override with a custom grader |
