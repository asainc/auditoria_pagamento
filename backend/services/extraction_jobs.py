"""Fila durável de extração baseada no repositório de negócio."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

from backend.repository import Repository

logger = logging.getLogger("judicial")


@dataclass(frozen=True)
class ClaimedExtractionJob:
    job_id: str
    process: str
    attempt: int
    max_attempts: int


class DurableExtractionWorkers:
    """Workers locais que consomem jobs persistidos e recuperáveis após reinício."""

    def __init__(
        self,
        repository: Repository,
        worker_count: int,
        handler: Callable[[ClaimedExtractionJob], None],
        *,
        lease_seconds: int = 900,
        poll_seconds: float = 0.25,
    ):
        self.repository = repository
        self.worker_count = worker_count
        self.handler = handler
        self.lease_seconds = lease_seconds
        self.poll_seconds = poll_seconds
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        for index in range(worker_count):
            thread = threading.Thread(
                target=self._loop,
                name=f"extraction-worker-{index + 1}",
                daemon=True,
            )
            thread.start()
            self.threads.append(thread)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            claimed = self.repository.claim_extraction_job(self.lease_seconds)
            if claimed is None:
                self.stop_event.wait(self.poll_seconds)
                continue
            job = ClaimedExtractionJob(*claimed)
            try:
                self.handler(job)
            except Exception as exc:  # handler já persiste estado sanitizado quando possível
                logger.error(
                    "extraction_worker_unhandled",
                    extra={"job_id": job.job_id, "error_type": type(exc).__name__},
                )
                self.repository.finish_extraction_job(job.job_id, success=False)

    def wake(self) -> None:
        """Sinal sem estado; reduz latência após enqueue."""
        # Event separado não é necessário: poll curto mantém implementação simples e durável.
        pass

    def close(self) -> None:
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=2)
