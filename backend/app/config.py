"""
Central configuration for the AI-Based Fake Identity / Document Screening backend (SIH PS-26188).
Keep tunable constants here instead of hardcoding them inline in services.
All authentication and security settings are environment-driven.
"""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Server & Environment ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # The legacy screening.db is retained untouched; use a clean V2 store by default.
    # Deployments that have a healthy legacy database can opt in explicitly with DATABASE_URL.
    f"sqlite:///{BASE_DIR / 'dataset' / 'screening_v2.db'}"
)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

# --- API Security & Authentication ---
API_KEYS = [
    key.strip()
    for key in os.getenv("API_KEYS", "test-api-key,admin-secret-key").split(",")
    if key.strip()
]
# SECURITY: Authentication is ON by default. Set REQUIRE_AUTH=false or DEV_MODE=true only for local dev.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")
# DEV_MODE=true explicitly bypasses auth for local development. Never use in production.
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
if DEV_MODE:
    REQUIRE_AUTH = False
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-demo-jwt-secret")
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "60"))
AUTH_USERS = json.loads(os.getenv("AUTH_USERS", '{"officer":"demo-officer","supervisor":"demo-supervisor","admin":"demo-admin","auditor":"demo-auditor"}'))
API_KEY_ROLES = json.loads(os.getenv("API_KEY_ROLES", '{"test-api-key":"admin","admin-secret-key":"admin"}'))
DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "demo-only-encryption-key-change-before-deployment")
EVIDENCE_RETENTION_DAYS = int(os.getenv("EVIDENCE_RETENTION_DAYS", "30"))

# --- Upload Limits & Security ---
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".mp4", ".mov", ".avi"}
# Strict MIME allowlist — application/octet-stream removed; video types added
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/tiff",
    "image/webp",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
}
# Magic byte signatures for supported image and video formats (strict file-content validation)
IMAGE_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",       # JPEG
    b"\x89PNG\r\n\x1a\n": "image/png",   # PNG
    b"RIFF": None,                         # WEBP or AVI
    b"II*\x00": "image/tiff",             # TIFF little-endian
    b"MM\x00*": "image/tiff",             # TIFF big-endian
    b"BM": "image/bmp",                   # BMP
}

# --- Risk scoring weights (must sum to 1.0) ---
RISK_WEIGHT_VALIDATION = float(os.getenv("RISK_WEIGHT_VALIDATION", "0.25"))
RISK_WEIGHT_TAMPERING = float(os.getenv("RISK_WEIGHT_TAMPERING", "0.35"))
RISK_WEIGHT_FACE_MISMATCH = float(os.getenv("RISK_WEIGHT_FACE_MISMATCH", "0.25"))
RISK_WEIGHT_REGISTRY = float(os.getenv("RISK_WEIGHT_REGISTRY", "0.15"))

# --- Risk label thresholds (inclusive lower bound, exclusive upper unless max) ---
RISK_LABEL_LOW_MAX = 30
RISK_LABEL_MEDIUM_MAX = 65
# > RISK_LABEL_MEDIUM_MAX => HIGH

# Face verification risk point contributions
FACE_MISMATCH_RISK_POINTS = 100.0
FACE_NO_SELFIE_RISK_POINTS = 0.0

# Registry (Blacklist / Duplicate) risk points
REGISTRY_BLACKLIST_HIT_POINTS = 100.0
REGISTRY_DUPLICATE_HIT_POINTS = 80.0

# --- Cross-Document Consistency Risk tunables ---
CROSS_DOC_DOB_MISMATCH_POINTS = float(os.getenv("CROSS_DOC_DOB_MISMATCH_POINTS", "30.0"))
CROSS_DOC_NAME_MISMATCH_POINTS = float(os.getenv("CROSS_DOC_NAME_MISMATCH_POINTS", "20.0"))
CROSS_DOC_GENERIC_MISMATCH_POINTS = float(os.getenv("CROSS_DOC_GENERIC_MISMATCH_POINTS", "10.0"))
CROSS_DOC_UNVERIFIED_MISMATCH_POINTS = float(os.getenv("CROSS_DOC_UNVERIFIED_MISMATCH_POINTS", "5.0"))
CROSS_DOC_MIN_CONFIDENCE_THRESHOLD = float(os.getenv("CROSS_DOC_MIN_CONFIDENCE_THRESHOLD", "0.55"))
CROSS_DOC_IDENTITY_LINK_FACE_THRESHOLD = float(os.getenv("CROSS_DOC_IDENTITY_LINK_FACE_THRESHOLD", "0.92"))

# --- OCR ---
EASYOCR_LANGS = ["en"]
MRZ_LINE_MIN_LENGTH = 30  # heuristic: lines >= this length are candidate MRZ lines

# --- Tampering detection tunables ---
ELA_JPEG_QUALITY = 90                   # quality used when resaving for Error Level Analysis
ELA_SUSPICIOUS_MEAN_THRESHOLD = 12.0    # mean pixel diff above this -> suspicious
ELA_SUSPICIOUS_MAX_THRESHOLD = 100.0    # any hotspot above this -> suspicious

# ORB copy-move tunables
COPY_MOVE_MIN_MATCHES = 10
COPY_MOVE_MIN_DISTANCE_PX = 40          # matched points closer than this are treated as same feature
ORB_MATCH_DISTANCE_THRESHOLD = 40       # Hamming distance cutoff for copy-move keypoint matches

# Stamp region analysis tunables
STAMP_MIN_RADIUS_PX = 15
STAMP_MAX_RADIUS_PX = 120
STAMP_SUSPICIOUS_ELA_THRESHOLD = 15.0

# Photo region analysis tunables
PHOTO_SEAM_EDGE_THRESHOLD = 0.28        # Canny edge density along photo bounding border
PHOTO_NOISE_RATIO_THRESHOLD = 2.5       # Ratio of photo noise variance vs document background
PHOTO_ELA_DELTA_THRESHOLD = 8.0         # Difference in mean ELA error inside vs outside photo

# EXIF suspicious software keywords
EDITING_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "affinity", "lightroom", "paint.net", "pixlr", "canva"
]

# Blend weights for tampering signals (must sum to 1.0)
WEIGHT_ELA = 0.25
WEIGHT_PHOTO_REGION = 0.20
WEIGHT_COPY_MOVE = 0.20
WEIGHT_CNN = 0.15
WEIGHT_STAMP = 0.10
WEIGHT_EXIF = 0.10

# --- Identity Cluster Risk Thresholds ---
# Cosine similarity bands for multiple-identity detection risk contribution
IDENTITY_CLUSTER_THRESHOLD_LOW = 0.82    # below this: no cluster risk
IDENTITY_CLUSTER_THRESHOLD_MED = 0.90    # 0.82-0.90 -> RISK_CLUSTER_LOW points
IDENTITY_CLUSTER_THRESHOLD_HIGH = 0.95   # 0.90-0.95 -> RISK_CLUSTER_MED points
# >= 0.95 -> RISK_CLUSTER_HIGH points
RISK_CLUSTER_LOW_POINTS = 15.0
RISK_CLUSTER_MED_POINTS = 25.0
RISK_CLUSTER_HIGH_POINTS = 35.0

# --- Audit Hash Versioning ---
AUDIT_HASH_VERSION = 2  # v1: legacy 7-field payload; v2: full 10-field payload

# --- Face verification ---
DEEPFACE_MODEL_NAME = "VGG-Face"     # solid accuracy/speed tradeoff for a demo
DEEPFACE_DISTANCE_METRIC = "cosine"

# --- Misc ---
TODAY_DATE_FORMAT = "%Y-%m-%d"
