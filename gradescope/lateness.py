import json
import os
import warnings
from datetime import datetime, timezone


def _parse_iso(timestamp_str):
    """Parse an ISO 8601 timestamp string into a timezone-aware datetime."""
    # Normalize trailing Z to +00:00 for fromisoformat compatibility
    normalized = timestamp_str.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


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


def compute_penalty(raw_score, metadata_path):
    """
    Apply the lateness penalty formula if the submission is late.

    Formula: final = on_time_score + 0.5 * (raw_score - on_time_score)
    If no on-time submission exists: final = 0.5 * raw_score
    If on time: final = raw_score (no penalty)
    If metadata is missing (local testing): return raw_score unchanged.
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

    submission_time = get_submission_time(metadata)

    if submission_time <= due_date:
        return raw_score

    # Submission is late
    on_time_score = get_best_ontime_score(metadata, due_date)
    if on_time_score is None:
        on_time_score = 0.0

    return on_time_score + 0.5 * (raw_score - on_time_score)


def describe_penalty(raw_score, final_score, metadata_path):
    """Return a human-readable description of the lateness penalty applied."""
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
        "on-time score {:.1f} + 0.5 \u00d7 ({:.1f} \u2212 {:.1f}) = {:.1f}"
    ).format(on_time_score, raw_score, on_time_score, final_score)
