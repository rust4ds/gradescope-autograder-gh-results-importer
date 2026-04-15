use super::*;

// ---- IO tests: input/output shown to students (visibility: visible) ----

/// io: sort_asc(&[3, 1, 2]) == [1, 2, 3]
#[test]
fn test_sort_asc_basic() {
    assert_eq!(sort_asc(&[3, 1, 2]), vec![1, 2, 3]);
}

/// io: sort_asc(&[]) == []
#[test]
fn test_sort_asc_empty() {
    assert_eq!(sort_asc(&[]), vec![]);
}

/// io: is_sorted(&[1, 2, 3]) == true
#[test]
fn test_is_sorted_true() {
    assert!(is_sorted(&[1, 2, 3]));
}

/// io: is_sorted(&[3, 1, 2]) == false
#[test]
fn test_is_sorted_false() {
    assert!(!is_sorted(&[3, 1, 2]));
}

// ---- Structural tests: hidden until after deadline (visibility: after_due_date) ----

/// structural: sort_asc preserves duplicates
#[test]
fn test_sort_asc_duplicates() {
    assert_eq!(sort_asc(&[3, 1, 3, 2]), vec![1, 2, 3, 3]);
}

/// structural: sort_asc with single element
#[test]
fn test_sort_asc_single() {
    assert_eq!(sort_asc(&[5]), vec![5]);
}

/// structural: is_sorted with single element is true
#[test]
fn test_is_sorted_single() {
    assert!(is_sorted(&[42]));
}

/// structural: is_sorted with equal elements is true
#[test]
fn test_is_sorted_equal() {
    assert!(is_sorted(&[5, 5, 5]));
}
