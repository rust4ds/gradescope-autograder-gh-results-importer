import json
import os
import warnings
from datetime import datetime, timezone


def _parse_iso(timestamp_str):
    # fromisoformat does not accept trailing Z before Python 3.11
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


def load_metadata(metadata_path):
    with open(metadata_path, "r") as f:
        return json.load(f)


def get_due_date(metadata):
    """Return the assignment due date as a timezone-aware datetime, or None."""
    due = metadata.get("assignment", {}).get("due_date")
    if not due:
        return None
    return _parse_iso(due)


def get_submission_time(metadata):
    """Return the current submission time as a timezone-aware datetime."""
    return _parse_iso(metadata["created_at"])


def get_best_ontime_score(metadata, due_date):
    """Return the highest score from previous submissions that were on time, or None."""
    previous = metadata.get("previous_submissions", [])
    candidates = []
    for sub in previous:
        sub_time_str = sub.get("submission_time") or sub.get("created_at")
        if not sub_time_str:
            continue
        sub_time = _parse_iso(sub_time_str)
        if sub_time <= due_date:
            score = sub.get("score")
            if score is not None:
                candidates.append(float(score))
    return max(candidates) if candidates else None


LATE_MULTIPLIER = 0.8  # late work earns 80% credit


def is_late(metadata_path):
    """True if the submission was made after the due date."""
    if not os.path.exists(metadata_path):
        return False
    try:
        metadata = load_metadata(metadata_path)
    except (json.JSONDecodeError, OSError):
        return False
    due = get_due_date(metadata)
    if due is None:
        return False
    return get_submission_time(metadata) > due


def get_due_date_from_path(metadata_path):
    """Convenience wrapper for grader.py."""
    if not os.path.exists(metadata_path):
        return None
    try:
        return get_due_date(load_metadata(metadata_path))
    except (json.JSONDecodeError, OSError):
        return None


def apply_penalty(current_score, ontime_score, late):
    """
    If late: ontime_score + LATE_MULTIPLIER * (current_score - ontime_score),
    floored at ontime_score so a student who broke their code post-deadline
    still gets credit for what they had at the deadline.
    Otherwise: current_score (no penalty).
    """
    if not late:
        return current_score
    if ontime_score is None:
        ontime_score = 0.0
    blended = ontime_score + LATE_MULTIPLIER * (current_score - ontime_score)
    return max(ontime_score, blended)


def describe(current_score, ontime_score, final_score, late):
    """Human-readable summary line for the score breakdown."""
    if not late:
        return "Score: {:.2f} (submitted on time)".format(current_score)
    if ontime_score is None:
        ontime_score = 0.0
    return (
        "Late submission. On-time (at deadline): {:.2f}, current: {:.2f}. "
        "Final: {:.2f} + {:.2f} * ({:.2f} - {:.2f}) = {:.2f}"
    ).format(
        ontime_score, current_score, ontime_score, LATE_MULTIPLIER,
        current_score, ontime_score, final_score,
    )


def compute_penalty(raw_score, metadata_path):
    """
    Legacy single-score API. Use is_late + apply_penalty for the new git-based flow.
    Falls back to using previous_submissions for the on-time score.
    """
    if not os.path.exists(metadata_path):
        warnings.warn(
            "Metadata file not found at {}. Returning raw score.".format(metadata_path)
        )
        return raw_score
    try:
        metadata = load_metadata(metadata_path)
    except (json.JSONDecodeError, OSError) as e:
        warnings.warn("Could not read metadata: {}. Returning raw score.".format(e))
        return raw_score
    due_date = get_due_date(metadata)
    if due_date is None:
        warnings.warn("No due_date in metadata. Returning raw score.")
        return raw_score
    if get_submission_time(metadata) <= due_date:
        return raw_score
    on_time_score = get_best_ontime_score(metadata, due_date) or 0.0
    return on_time_score + LATE_MULTIPLIER * (raw_score - on_time_score)


def describe_penalty(raw_score, final_score, metadata_path):
    """Legacy describe API matching compute_penalty."""
    if not os.path.exists(metadata_path):
        return "Score: {:.1f}".format(raw_score)
    try:
        metadata = load_metadata(metadata_path)
        due_date = get_due_date(metadata)
        submission_time = get_submission_time(metadata)
    except Exception:
        return "Score: {:.1f}".format(raw_score)
    if due_date is None or submission_time <= due_date:
        return "Score: {:.1f} (submitted on time)".format(raw_score)
    on_time_score = get_best_ontime_score(metadata, due_date) or 0.0
    return (
        "Late submission penalty applied: "
        "on-time score {:.1f} + {:.1f}x ({:.1f} - {:.1f}) = {:.1f}"
    ).format(on_time_score, LATE_MULTIPLIER, raw_score, on_time_score, final_score)
