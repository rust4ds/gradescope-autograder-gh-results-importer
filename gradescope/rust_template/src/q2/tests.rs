use super::*;

// ---- IO tests: input/output shown to students (visibility: visible) ----

/// io: max_value(&[3, 1, 4, 1, 5]) == Some(5)
#[test]
fn test_max_value_basic() {
    assert_eq!(max_value(&[3, 1, 4, 1, 5]), Some(5));
}

/// io: max_value(&[]) == None
#[test]
fn test_max_value_empty() {
    assert_eq!(max_value(&[]), None);
}

/// io: count_if(&[1,2,3,4], |x| x % 2 == 0) == 2
#[test]
fn test_count_if_even() {
    assert_eq!(count_if(&[1, 2, 3, 4], |x| x % 2 == 0), 2);
}

/// io: count_if(&[], |x| x > 0) == 0
#[test]
fn test_count_if_empty() {
    assert_eq!(count_if(&[], |x| x > 0), 0);
}

// ---- Structural tests: hidden until after deadline (visibility: after_due_date) ----

/// structural: max_value with single element
#[test]
fn test_max_value_single() {
    assert_eq!(max_value(&[42]), Some(42));
}

/// structural: max_value with all equal elements
#[test]
fn test_max_value_all_equal() {
    assert_eq!(max_value(&[7, 7, 7]), Some(7));
}

/// structural: count_if with no matches
#[test]
fn test_count_if_no_match() {
    assert_eq!(count_if(&[1, 3, 5], |x| x % 2 == 0), 0);
}

/// structural: count_if with all matches
#[test]
fn test_count_if_all_match() {
    assert_eq!(count_if(&[2, 4, 6], |x| x % 2 == 0), 3);
}
