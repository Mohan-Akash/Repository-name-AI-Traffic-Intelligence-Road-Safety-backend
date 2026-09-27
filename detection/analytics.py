from collections import defaultdict
import math


class TrafficAnalytics:
    """Reusable traffic analytics for tracked vehicles."""

    def __init__(self, min_track_frames=15):
        self.min_track_frames = min_track_frames
        self.track_history = defaultdict(list)
        self.vehicle_classes = defaultdict(list)

    def update(self, track_id, vehicle_type, center_x, center_y):
        self.track_history[track_id].append((center_x, center_y))
        self.vehicle_classes[track_id].append(vehicle_type)

    def calculate_speed(self, positions):
        if len(positions) < 2:
            return 0.0

        distances = []
        for i in range(1, len(positions)):
            x1, y1 = positions[i - 1]
            x2, y2 = positions[i]
            distances.append(math.hypot(x2 - x1, y2 - y1))

        return sum(distances) / len(distances) if distances else 0.0

    def calculate_direction(self, positions):
        if len(positions) < 2:
            return "STATIONARY"

        x1, y1 = positions[0]
        x2, y2 = positions[-1]
        dx, dy = x2 - x1, y2 - y1
        threshold = 2

        if abs(dx) < threshold and abs(dy) < threshold:
            return "STATIONARY"
        if dx > threshold and dy > threshold:
            return "DOWN-RIGHT"
        if dx < -threshold and dy > threshold:
            return "DOWN-LEFT"
        if dx > threshold and dy < -threshold:
            return "UP-RIGHT"
        if dx < -threshold and dy < -threshold:
            return "UP-LEFT"
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > 0 else "LEFT"
        return "DOWN" if dy > 0 else "UP"

    def get_vehicle_type(self, track_id):
        classes = self.vehicle_classes.get(track_id, [])
        if not classes:
            return "unknown"
        return max(set(classes), key=classes.count)

    def get_results(self):
        results = []

        for track_id, positions in self.track_history.items():
            if len(positions) < self.min_track_frames:
                continue

            results.append({
                "vehicle_id": int(track_id),
                "vehicle_type": self.get_vehicle_type(track_id),
                "direction": self.calculate_direction(positions),
                "speed_px_frame": round(
                    self.calculate_speed(positions), 2
                ),
                "track_frames": len(positions),
            })

        return results
