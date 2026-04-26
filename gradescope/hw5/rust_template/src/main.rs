mod q1;
use q1::*;

fn main() {
    let dataset = vec![
        DataPoint::new(vec![1.0, 2.0], 0),
        DataPoint::new(vec![3.0, 4.0], 0),
        DataPoint::new(vec![5.0, 1.0], 1),
        DataPoint::new(vec![7.0, 8.0], 1),
        DataPoint::new(vec![2.0, 5.0], 0),
    ];
    let query = DataPoint::new(vec![3.0, 3.0], -1);

    println!("Query point: {:?}", query);

    let manhattan: Vec<f64> = dataset.iter().map(|p| query.manhattan_distance(p)).collect();
    println!("Manhattan distances: {:?}", manhattan);

    let euclidean: Vec<f64> = dataset.iter().map(|p| query.euclidean_distance(p)).collect();
    println!("Euclidean distances: {:?}", euclidean);

    println!("Nearest neighbor index: {:?}", nearest_neighbor_index(&query, &dataset));
    println!("Nearest neighbor label: {:?}", nearest_neighbor_label(&query, &dataset));
    println!("Points within radius 2.5: {:?}", points_within_radius(&query, &dataset, 2.5));
}
