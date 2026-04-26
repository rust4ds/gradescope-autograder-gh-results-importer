use super::*;

#[test]
fn manhattan_distance_test_cases() {
    let a = DataPoint::new(vec![0.0, 0.0], 0);
    let b = DataPoint::new(vec![3.0, 4.0], 1);
    assert!((a.manhattan_distance(&b) - 7.0).abs() < 1e-9);

    let c = DataPoint::new(vec![1.0, 1.0], 0);
    let d = DataPoint::new(vec![4.0, 5.0], 0);
    assert!((c.manhattan_distance(&d) - 7.0).abs() < 1e-9);

    // Symmetry
    assert!((b.manhattan_distance(&a) - 7.0).abs() < 1e-9);

    // Same point
    let e = DataPoint::new(vec![2.0, 3.0], 0);
    assert!((e.manhattan_distance(&e) - 0.0).abs() < 1e-9);

    // Negative coordinates
    let f = DataPoint::new(vec![-1.0, -2.0], 0);
    let g = DataPoint::new(vec![1.0, 2.0], 0);
    assert!((f.manhattan_distance(&g) - 6.0).abs() < 1e-9);
}

#[test]
fn euclidean_distance_test_cases() {
    let a = DataPoint::new(vec![0.0, 0.0], 0);
    let b = DataPoint::new(vec![3.0, 4.0], 1);
    assert!((a.euclidean_distance(&b) - 5.0).abs() < 1e-9);

    // Same point → 0
    assert!((a.euclidean_distance(&a) - 0.0).abs() < 1e-9);

    // Symmetry
    assert!((b.euclidean_distance(&a) - 5.0).abs() < 1e-9);

    // 3D
    let c = DataPoint::new(vec![1.0, 2.0, 2.0], 0);
    let d = DataPoint::new(vec![4.0, 6.0, 2.0], 0);
    assert!((c.euclidean_distance(&d) - 5.0).abs() < 1e-9);

    // Unit distance
    let e = DataPoint::new(vec![0.0], 0);
    let f = DataPoint::new(vec![1.0], 0);
    assert!((e.euclidean_distance(&f) - 1.0).abs() < 1e-9);
}

#[test]
fn all_distances_test_cases() {
    let query = DataPoint::new(vec![0.0, 0.0], 0);
    let data = vec![
        DataPoint::new(vec![3.0, 4.0], 1),
        DataPoint::new(vec![0.0, 1.0], 0),
        DataPoint::new(vec![1.0, 0.0], 0),
    ];
    let dists = all_distances(&query, &data);
    assert_eq!(dists.len(), 3);
    assert!((dists[0] - 5.0).abs() < 1e-9);
    assert!((dists[1] - 1.0).abs() < 1e-9);
    assert!((dists[2] - 1.0).abs() < 1e-9);

    // Empty dataset
    let empty: Vec<DataPoint> = vec![];
    assert_eq!(all_distances(&query, &empty), vec![]);
}

#[test]
fn nearest_neighbor_index_test_cases() {
    let query = DataPoint::new(vec![0.0, 0.0], 0);
    let data = vec![
        DataPoint::new(vec![10.0, 10.0], 0),
        DataPoint::new(vec![1.0, 1.0], 1),
        DataPoint::new(vec![5.0, 5.0], 0),
    ];
    assert_eq!(nearest_neighbor_index(&query, &data), Some(1));

    // Empty → None
    let empty: Vec<DataPoint> = vec![];
    assert_eq!(nearest_neighbor_index(&query, &empty), None);

    // Single element
    let single = vec![DataPoint::new(vec![3.0, 4.0], 7)];
    assert_eq!(nearest_neighbor_index(&query, &single), Some(0));
}

#[test]
fn nearest_neighbor_label_test_cases() {
    let query = DataPoint::new(vec![0.0, 0.0], 0);
    let data = vec![
        DataPoint::new(vec![10.0, 10.0], 0),
        DataPoint::new(vec![1.0, 1.0], 42),
        DataPoint::new(vec![5.0, 5.0], 0),
    ];
    assert_eq!(nearest_neighbor_label(&query, &data), Some(42));

    // Empty → None
    let empty: Vec<DataPoint> = vec![];
    assert_eq!(nearest_neighbor_label(&query, &empty), None);

    let single = vec![DataPoint::new(vec![3.0, 4.0], 7)];
    assert_eq!(nearest_neighbor_label(&query, &single), Some(7));
}

#[test]
fn points_within_radius_test_cases() {
    let query = DataPoint::new(vec![0.0, 0.0], 0);
    let data = vec![
        DataPoint::new(vec![1.0, 0.0], 0), // dist = 1
        DataPoint::new(vec![3.0, 4.0], 1), // dist = 5
        DataPoint::new(vec![0.0, 2.0], 0), // dist = 2
        DataPoint::new(vec![0.0, 3.0], 1), // dist = 3
    ];
    let within = points_within_radius(&query, &data, 2.0);
    assert_eq!(within.len(), 2);
    assert!(within.contains(&0));
    assert!(within.contains(&2));

    // Exact boundary included
    let within2 = points_within_radius(&query, &data, 3.0);
    assert!(within2.contains(&3));

    // Radius 0 → only coincident points
    let within3 = points_within_radius(&query, &data, 0.0);
    assert_eq!(within3.len(), 0);

    // Empty dataset
    let empty: Vec<DataPoint> = vec![];
    assert_eq!(points_within_radius(&query, &empty, 5.0), vec![]);
}
