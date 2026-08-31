"""
Pydantic response and request models for Swagger API documentation and type validation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Consistent error shape documented for all protected API routes."""
    detail: str = Field(..., examples=["Invalid or missing X-API-Key header."])


# --- OCR Models ---
class OCRResponse(BaseModel):
    document_type: str = Field(..., examples=["PASSPORT"])
    fields: Dict[str, Any] = Field(default_factory=dict, description="Each field has value, confidence, extraction_source, and validation_status")
    confidence: Dict[str, Any] = Field(default_factory=dict)
    raw_mrz: Optional[List[str]] = None
    engine: str = Field(..., examples=["PassportEye_MRZ"])
    error: Optional[str] = None


# --- Validation Models ---
class CheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


class ValidationResponse(BaseModel):
    valid: bool
    document_type: str
    checks: List[Dict[str, Any]]
    pass_count: int
    fail_count: int
    error: Optional[str] = None
    passed_rules: List[Dict[str, Any]] = Field(default_factory=list)
    failed_rules: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence: float = 0.0


# --- Tampering Models ---
class TamperingCheckDetail(BaseModel):
    name: str
    triggered: bool
    score: float
    detail: str


class TamperingResponse(BaseModel):
    tampering_score: float
    checks: List[TamperingCheckDetail]
    error: Optional[str] = None
    detectors: Dict[str, float] = Field(default_factory=dict)
    heatmap: Optional[Dict[str, Any]] = None


class CNNScoreResponse(BaseModel):
    cnn_score: float
    model: str
    triggered: bool
    detail: str
    error: Optional[str] = None


# --- Face Verification Models ---
class FaceVerifyResponse(BaseModel):
    match: Optional[bool] = None
    distance: Optional[float] = None
    threshold: Optional[float] = None
    model: Optional[str] = "VGG-Face"
    error: Optional[str] = None
    document_face_confidence: Optional[float] = None
    live_face_confidence: Optional[float] = None
    cosine_similarity: Optional[float] = None


# --- Registry / Blacklist Models ---
class RegistryCheckResponse(BaseModel):
    is_duplicate: bool
    is_blacklisted: bool
    matched_records: List[Dict[str, Any]]
    flags: List[str]
    error: Optional[str] = None


class BlacklistCreateRequest(BaseModel):
    document_number: str = Field(..., examples=["A12345678"])
    reason: str = Field(..., examples=["Reported lost in INTERPOL database"])
    country: Optional[str] = Field(None, examples=["USA"])
    document_type: Optional[str] = None
    severity: str = "medium"
    status: str = "active"


class BlacklistResponse(BaseModel):
    id: int
    document_number: str
    reason: str
    country: Optional[str]
    added_at: Optional[str]
    document_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None


# --- Combined Risk Assessment Model ---
class RiskAssessResponse(BaseModel):
    risk_score: float = Field(..., examples=[12.5], description="0-100 composite risk; higher requires greater scrutiny.")
    risk_label: str = Field(..., examples=["LOW"])
    component_scores: Dict[str, float]
    flags: List[str]
    ocr: Optional[Dict[str, Any]] = None
    modules: Dict[str, Any]
    record_id: Optional[str] = None
    risk_category: Optional[str] = None
    decision: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[str] = None


# --- History Audit Trail Models ---
class ScreeningHistoryItem(BaseModel):
    id: str
    document_type: Optional[str]
    document_number: Optional[str]
    holder_name: Optional[str]
    risk_score: float
    risk_label: str
    flags: List[str]
    created_at: Optional[str]


class ScreeningHistoryListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ScreeningHistoryItem]
