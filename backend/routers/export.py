"""IFC and other model export endpoints."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from core.ifc_writer import export_topology_to_ifc
from schemas.export import ExportIfcRequest

router = APIRouter(prefix="/api/export", tags=["export"])

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str, *, default: str = "steelera.ifc") -> str:
    base = Path(name).name.strip() or default
    if not base.lower().endswith(".ifc"):
        base = f"{base}.ifc"
    cleaned = _SAFE_NAME.sub("_", base)
    return cleaned or default


def _unlink_temp(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


@router.post("/ifc")
async def export_ifc(
    body: ExportIfcRequest,
    background_tasks: BackgroundTasks,
) -> FileResponse:
    """Build an IFC file from ``structural_topology`` and return it as a download."""
    topology = body.structural_topology
    if not topology.get("entities"):
        raise HTTPException(
            status_code=422,
            detail="structural_topology has no entities. Generate a shed first.",
        )

    building_id = str(topology.get("building_id", "shed_1"))
    default_name = f"{building_id}.ifc"
    filename = _safe_filename(body.filename or default_name, default=default_name)

    fd, temp_path = tempfile.mkstemp(suffix=".ifc", prefix="steelera_")
    os.close(fd)

    try:
        ok = export_topology_to_ifc(
            topology,
            temp_path,
            schema_version=body.schema_version,
        )
        if not ok:
            _unlink_temp(temp_path)
            raise HTTPException(
                status_code=500,
                detail="IFC export failed. Check backend logs for details.",
            )

        background_tasks.add_task(_unlink_temp, temp_path)
        return FileResponse(
            path=temp_path,
            media_type="application/x-ifc",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        _unlink_temp(temp_path)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
