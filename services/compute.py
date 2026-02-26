"""
Compute service: execute tasks for SOL payments.
Another revenue source for the Virus agent.
"""

import uuid
import time
from dataclasses import dataclass
from typing import Optional


COMPUTE_PRICE_SOL = 0.01


@dataclass
class ComputeJob:
    job_id: str
    task_type: str
    payload: dict
    status: str = "pending"
    result: Optional[dict] = None
    created_at: float = 0.0
    completed_at: Optional[float] = None
    payment_signature: str = ""


class ComputeService:
    def __init__(self, sol_wallet, payment_verifier):
        self.sol_wallet = sol_wallet
        self.payments = payment_verifier
        self._jobs: dict[str, ComputeJob] = {}
        self._total_revenue_sol: float = 0.0

    async def submit_job(
        self, task_type: str, payload: dict, payment_signature: str
    ) -> dict:
        """Submit a compute job after payment verification."""
        verified = await self.payments.verify_and_record(
            payment_signature, self.sol_wallet, COMPUTE_PRICE_SOL
        )
        if not verified:
            return {"error": "Payment verification failed"}

        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = ComputeJob(
            job_id=job_id,
            task_type=task_type,
            payload=payload,
            created_at=time.time(),
            payment_signature=payment_signature,
        )
        self._jobs[job_id] = job

        result = await self._execute(job)

        job.status = "completed"
        job.result = result
        job.completed_at = time.time()
        self._total_revenue_sol += COMPUTE_PRICE_SOL

        return {
            "job_id": job_id,
            "status": "completed",
            "result": result,
        }

    def get_job(self, job_id: str) -> Optional[dict]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status,
            "result": job.result,
            "created_at": job.created_at,
        }

    async def _execute(self, job: ComputeJob) -> dict:
        """Execute a compute task. Extensible by task_type."""
        if job.task_type == "echo":
            return {"echo": job.payload}

        if job.task_type == "hash":
            import hashlib
            data = job.payload.get("data", "")
            return {
                "sha256": hashlib.sha256(data.encode()).hexdigest(),
            }

        return {"error": f"Unknown task type: {job.task_type}"}
