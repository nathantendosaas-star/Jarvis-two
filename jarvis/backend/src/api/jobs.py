"""Jobs API router — exposes job status polling and the script completion callback."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models.job import Job
from ..schemas.job import JobResponse, JobStatusResponse, JobCompleteRequest

router = APIRouter()


@router.get("/", response_model=List[JobStatusResponse])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """Return the 20 most recent jobs (newest first)."""
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(20)
    )
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Return full detail for a single job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


@router.post("/{job_id}/complete")
async def complete_job(
    job_id: str,
    body: JobCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Callback endpoint — called by the script itself when it finishes.

    The script POSTs here with the output file path and optional row count.
    This is idempotent: if the job is already 'done', the call is a no-op.
    """
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    # Idempotent guard — only transition from running → done
    if job.status == "running":
        job.status = "done"
        job.output_path = body.output_path
        job.finished_at = datetime.now(timezone.utc)
        # exit_code will be set by the watcher from the process returncode;
        # pre-set to 0 here as the script self-reported success
        if job.exit_code is None:
            job.exit_code = 0

    return {"ok": True, "job_id": job_id, "status": job.status}
