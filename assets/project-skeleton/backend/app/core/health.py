################################################################################
# @Project: ai-assistant
# @File Path: backend/app/core/health.py
# @Description: Liveness endpoint used by orchestrators and smoke tests
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

# Third-Party Libraries
from fastapi import APIRouter

################################################################################
# Module Constants
################################################################################
# 路由对象由 main 统一挂载，保持与业务路由一致的装配方式
router = APIRouter(tags=["system"])


################################################################################
# Module Functions
################################################################################
@router.get("/health")
async def health() -> dict[str, str]:
    """
    Report process liveness for orchestrator probes.

    This endpoint must stay dependency free: it answers whether the process is
    able to serve traffic, not whether every downstream system is healthy.

    :return: Constant payload with a single ``status`` field.
    """
    return {"status": "ok"}
