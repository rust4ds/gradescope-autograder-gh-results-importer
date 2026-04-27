#[derive(Debug, Clone, PartialEq)]
pub struct DataPoint {
    pub features: Vec<f64>,
    pub label: i32,
}

impl DataPoint {
    pub fn new(features: Vec<f64>, label: i32) -> Self {
        DataPoint { features, label }
    }

    pub fn manhattan_distance(&self, other: &DataPoint) -> f64 {
        todo!()
    }

    pub fn euclidean_distance(&self, other: &DataPoint) -> f64 {
        todo!()
    }
}

pub fn all_distances(query: &DataPoint, data: &[DataPoint]) -> Vec<f64> {
    todo!()
}

pub fn nearest_neighbor_index(query: &DataPoint, data: &[DataPoint]) -> Option<usize> {
    todo!()
}

pub fn nearest_neighbor_label(query: &DataPoint, data: &[DataPoint]) -> Option<i32> {
    todo!()
}

pub fn points_within_radius(query: &DataPoint, data: &[DataPoint], r: f64) -> Vec<usize> {
    todo!()
}

#[cfg(test)]
mod tests;
