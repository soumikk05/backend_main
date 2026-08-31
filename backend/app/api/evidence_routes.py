"""Authenticated access to local evidence artifacts; no public static exposure."""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.auth import require_roles
from app.services.evidence_service import ROOT
from app.services.privacy_service import purge_expired_evidence

router = APIRouter(tags=["evidence"])

@router.get("/evidence/{screening_id}/{filename}")
def download_evidence(screening_id: str, filename: str, _: dict = Depends(require_roles("officer", "supervisor", "admin", "auditor"))):
    if Path(filename).name != filename: raise HTTPException(400, "Invalid evidence filename")
    path = ROOT / screening_id / filename
    if not path.is_file(): raise HTTPException(404, "Evidence artifact not found")
    return FileResponse(path)

@router.post("/api/privacy/purge")
def purge_evidence(_: dict = Depends(require_roles("admin"))):
    return {"removed_files": purge_expired_evidence(str(ROOT))}
