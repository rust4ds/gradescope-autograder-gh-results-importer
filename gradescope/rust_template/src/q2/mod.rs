/// Returns the maximum value in a slice, or None if empty.
pub fn max_value(values: &[i32]) -> Option<i32> {
    unimplemented!()
}

/// Returns the number of elements in a slice that satisfy the predicate.
pub fn count_if<F: Fn(i32) -> bool>(values: &[i32], predicate: F) -> usize {
    unimplemented!()
}

#[cfg(test)]
pub mod tests;
