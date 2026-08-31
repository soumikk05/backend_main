"""Backwards-compatible root endpoint for the documented screening pipeline."""
from fastapi import APIRouter
from app.api.risk_score_routes import assess
from app.models.schemas import RiskAssessResponse

router = APIRouter(tags=["screening"])
router.add_api_route("/screen", assess, methods=["POST"], response_model=RiskAssessResponse)
