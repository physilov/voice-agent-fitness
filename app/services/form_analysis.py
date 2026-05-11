"""
Real-time exercise form analysis.

The client (web/app) runs MediaPipe Pose and streams landmark keypoints via
WebSocket. This service compares keypoints against reference angle ranges for
each exercise and returns coaching cues. The agent only sees the post-session
summary — not the raw stream.

MediaPipe landmark order: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
"""
import math
from dataclasses import dataclass

_LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

_SQUAT_ALIASES = {"squat", "barbell_squat", "goblet_squat", "front_squat", "hack_squat"}


@dataclass
class Landmark:
    x: float
    y: float
    z: float
    visibility: float


def _angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    """Angle in degrees at joint b."""
    ab = (a.x - b.x, a.y - b.y)
    cb = (c.x - b.x, c.y - b.y)
    dot = ab[0] * cb[0] + ab[1] * cb[1]
    mag = math.sqrt(ab[0] ** 2 + ab[1] ** 2) * math.sqrt(cb[0] ** 2 + cb[1] ** 2)
    if mag == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / mag))))


def _parse_landmarks(raw: list[dict]) -> dict[str, Landmark]:
    return {name: Landmark(**lm) for name, lm in zip(_LANDMARK_NAMES, raw)}


def _analyze_squat(landmarks: dict[str, Landmark]) -> list[str]:
    cues = []
    needed = {"left_hip", "left_knee", "left_ankle"}
    if not needed.issubset(landmarks):
        return cues

    knee_angle = _angle(landmarks["left_hip"], landmarks["left_knee"], landmarks["left_ankle"])
    if knee_angle > 110:
        cues.append("Go deeper — aim for thighs parallel to the floor")
    elif knee_angle < 65:
        cues.append("You're going too deep — stop at parallel")

    return cues


def analyze_frame(exercise: str, landmarks_raw: list[dict]) -> list[str]:
    """Return real-time coaching cues for one pose frame. Empty list = form looks good."""
    landmarks = _parse_landmarks(landmarks_raw)
    if exercise.lower().replace(" ", "_") in _SQUAT_ALIASES:
        return _analyze_squat(landmarks)
    return []
