use super::*;

// ---- IO tests: input/output shown to students (visibility: visible) ----

/// io: add(2, 3) == 5
#[test]
fn test_add_positive() {
    assert_eq!(add(2, 3), 5);
}

/// io: add(-1, -2) == -3
#[test]
fn test_add_negative() {
    assert_eq!(add(-1, -2), -3);
}

/// io: is_even(4) == true
#[test]
fn test_is_even_true() {
    assert!(is_even(4));
}

/// io: is_even(3) == false
#[test]
fn test_is_even_false() {
    assert!(!is_even(3));
}

// ---- Structural tests: hidden until after deadline (visibility: after_due_date) ----

/// structural: add(0, 0) == 0
#[test]
fn test_add_zero() {
    assert_eq!(add(0, 0), 0);
}

/// structural: add handles i32::MAX + 0
#[test]
fn test_add_identity() {
    assert_eq!(add(i32::MAX, 0), i32::MAX);
}

/// structural: is_even(0) == true
#[test]
fn test_is_even_zero() {
    assert!(is_even(0));
}

/// structural: is_even(-2) == true
#[test]
fn test_is_even_negative_even() {
    assert!(is_even(-2));
}
