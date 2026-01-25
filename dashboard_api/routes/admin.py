"""Admin endpoints for data refresh operations.

All endpoints in this module require authentication via the X-Admin-API-Key header.
Set the ADMIN_API_KEY environment variable to enable these endpoints.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin_api_key

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helper functions (no auth, called by endpoints)
# ---------------------------------------------------------------------------


def _run_russell_refresh() -> dict[str, str]:
    """Execute the Russell 2000 refresh command."""
    project_root = Path(__file__).parent.parent.parent

    result = subprocess.run(
        [sys.executable, "main.py", "refresh-russell"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error(f"Russell refresh failed: {result.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"Russell refresh failed: {result.stderr or 'Unknown error'}",
        )

    logger.info("Russell 2000 refresh completed successfully")
    return {
        "status": "success",
        "message": "Russell 2000 constituent list refreshed successfully",
        "output": result.stdout,
    }


def _run_fundamentals_refresh(
    include_russell: bool,
    include_sp500: bool,
    limit: int,
) -> dict[str, str]:
    """Execute the fundamentals refresh command."""
    project_root = Path(__file__).parent.parent.parent

    cmd = [sys.executable, "main.py", "refresh-fundamentals", "--limit", str(limit)]
    if include_russell:
        cmd.append("--include-russell")
    if include_sp500:
        cmd.append("--include-sp500")

    result = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        logger.error(f"Fundamentals refresh failed: {result.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"Fundamentals refresh failed: {result.stderr or 'Unknown error'}",
        )

    logger.info("Fundamentals refresh completed successfully")
    return {
        "status": "success",
        "message": "Fundamentals cache refreshed successfully",
        "parameters": {
            "include_russell": include_russell,
            "include_sp500": include_sp500,
            "limit": limit,
        },
        "output": result.stdout,
    }


# ---------------------------------------------------------------------------
# API Endpoints (all protected with API key authentication)
# ---------------------------------------------------------------------------


@router.post("/refresh-russell")
async def refresh_russell(
    _: str = Depends(require_admin_api_key),
) -> dict[str, str]:
    """
    Refresh Russell 2000 constituent list.

    This endpoint triggers the CLI command to download the latest
    Russell 2000 constituents and save them to data/universe/russell_2000.csv.

    **Authentication:** Requires `X-Admin-API-Key` header.

    **Note:** This operation may take several seconds to complete.
    """
    try:
        return _run_russell_refresh()
    except subprocess.TimeoutExpired:
        logger.error("Russell refresh timed out")
        raise HTTPException(
            status_code=504,
            detail="Russell refresh operation timed out (>120s)",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Russell refresh error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh Russell 2000: {str(e)}",
        )


@router.post("/refresh-fundamentals")
async def refresh_fundamentals(
    include_russell: bool = True,
    include_sp500: bool = True,
    limit: int = 200,
    _: str = Depends(require_admin_api_key),
) -> dict[str, str]:
    """
    Refresh fundamentals cache for universe symbols.

    This endpoint triggers the CLI command to fetch fundamentals data
    from Alpha Vantage for the seed universe, optionally including
    Russell 2000 and S&P 500 constituents.

    **Authentication:** Requires `X-Admin-API-Key` header.

    **Parameters:**
    - **include_russell**: Include Russell 2000 constituents (default: true)
    - **include_sp500**: Include S&P 500 constituents (default: true)
    - **limit**: Maximum number of symbols to refresh (default: 200)

    **Note:** This operation may take several minutes due to API rate limits.
    **Warning:** Free tier Alpha Vantage is limited to 5 calls/minute.
    """
    try:
        return _run_fundamentals_refresh(include_russell, include_sp500, limit)
    except subprocess.TimeoutExpired:
        logger.error("Fundamentals refresh timed out")
        raise HTTPException(
            status_code=504,
            detail="Fundamentals refresh timed out (>10min). Try reducing the limit parameter.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fundamentals refresh error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh fundamentals: {str(e)}",
        )


@router.post("/refresh-all")
async def refresh_all(
    _: str = Depends(require_admin_api_key),
) -> dict[str, str]:
    """
    Refresh both Russell 2000 constituents and fundamentals cache.

    This is a convenience endpoint that runs both refresh operations
    sequentially: Russell 2000 first, then fundamentals.

    **Authentication:** Requires `X-Admin-API-Key` header.

    **Note:** This operation may take 10+ minutes to complete due to
    API rate limits.
    """
    try:
        # Use internal helpers directly (auth already verified by this endpoint)
        russell_result = _run_russell_refresh()
        fundamentals_result = _run_fundamentals_refresh(
            include_russell=True,
            include_sp500=True,
            limit=200,
        )

        return {
            "status": "success",
            "message": "All data refreshed successfully",
            "russell": russell_result,
            "fundamentals": fundamentals_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full refresh error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete full refresh: {str(e)}",
        )


@router.get("/refresh-status")
async def refresh_status(
    _: str = Depends(require_admin_api_key),
) -> dict[str, str | dict]:
    """
    Check the status of cached data files.

    Returns information about when Russell 2000 and fundamentals
    data was last updated.

    **Authentication:** Requires `X-Admin-API-Key` header.
    """
    try:
        project_root = Path(__file__).parent.parent.parent

        russell_file = project_root / "data" / "universe" / "russell_2000.csv"
        fundamentals_dir = project_root / "data" / "universe" / "fundamentals"

        status = {
            "russell_2000": {
                "exists": russell_file.exists(),
                "last_modified": None,
            },
            "fundamentals_cache": {
                "exists": fundamentals_dir.exists(),
                "file_count": 0,
            },
        }

        if russell_file.exists():
            import datetime
            mtime = russell_file.stat().st_mtime
            status["russell_2000"]["last_modified"] = datetime.datetime.fromtimestamp(mtime).isoformat()

        if fundamentals_dir.exists():
            status["fundamentals_cache"]["file_count"] = len(list(fundamentals_dir.glob("*.json")))

        return {
            "status": "success",
            "data": status,
        }

    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check refresh status: {str(e)}",
        )
