import requests

API_URL = "http://127.0.0.1:8000/vehicles"


def save_vehicle(vehicle):
    try:
        response = requests.post(
            API_URL,
            json={
                "vehicle_id": vehicle["vehicle_id"],
                "vehicle_type": vehicle["vehicle_type"],
                "direction": vehicle["direction"],
                "speed_px_frame": vehicle["speed_px_frame"],
                "camera_id": "camera_1",
            },
            timeout=5,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        print(f"API error: {e}")
        return None