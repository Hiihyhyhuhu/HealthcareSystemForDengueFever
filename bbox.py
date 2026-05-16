import numpy as np
from scipy.optimize import linear_sum_assignment

iou_matrix = np.array([
    [0.8, 0.1],
    [0.2, 0.0],
    [0.3, 0.9]
])

cost_matrix = 1 - iou_matrix
row_indices, col_indices = linear_sum_assignment(cost_matrix)
total_iou = 0
for track_idx, bbox_idx in zip(row_indices, col_indices):
    print(track_idx, bbox_idx)
    score = iou_matrix[track_idx, bbox_idx]
    total_iou += score
    print(score)

all_tracks = set(range(iou_matrix.shape[0]))
matched_tracks = set(row_indices)
unmatched_tracks = all_tracks - matched_tracks
print("Unmatched tracks:", unmatched_tracks)