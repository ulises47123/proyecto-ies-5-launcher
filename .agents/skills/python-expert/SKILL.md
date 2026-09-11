---
name: python-expert
description: >-
  Mastery-level Python engineering guide, clean code architecture, type hinting,
  concurrency (asyncio & ThreadPoolExecutor), memory efficiency, and SOLID design patterns.
---

# Python Expert Skill Guide

This skill establishes advanced engineering standards for writing clean, robust, maintainable, and high-performance Python applications.

---

## 1. Clean Architecture & SOLID Principles

- **Single Responsibility Principle (SRP)**: Each class or module must have one, and only one, reason to change (e.g. separate scraping logic from Pyloid GUI/IPC bridge).
- **Type Annotations**: Always annotate function signatures and dataclasses.

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class UserProfile:
    dni: str
    nombre: str
    email: Optional[str] = None
    foto_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dni": self.dni,
            "nombre": self.nombre,
            "email": self.email or "No especificado",
            "foto_url": self.foto_url or ""
        }
```

---

## 2. Non-Blocking Concurrency & Threading

- **GUI & Qt Compatibility**: Never call blocking methods (`time.sleep()`, `requests.get()`, `future.result()`) directly inside main looper/event loops.
- **Worker Pools**: Use `ThreadPoolExecutor` or `asyncio.to_thread` for asynchronous background jobs.

```python
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor

class AsyncJobManager:
    def __init__(self, max_workers: int = 4):
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def submit_job(self, func, *args, **kwargs) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {"done": False, "result": None}

        def _worker():
            try:
                res = func(*args, **kwargs)
                self._jobs[job_id] = {"done": True, "result": res}
            except Exception as e:
                logging.exception(f"Job {job_id} failed")
                self._jobs[job_id] = {"done": True, "result": {"ok": False, "error": str(e)}}

        self._pool.submit(_worker)
        return job_id

    def poll_job(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id, {"done": True, "result": None})
        if job.get("done"):
            self._jobs.pop(job_id, None)  # Prevent memory leaks
        return job
```

---

## 3. Exception Handling & Logging

- Never swallow exceptions silently with bare `except: pass`.
- Log full tracebacks when encountering unexpected errors.
- Always clean up external resources with context managers (`with` statements).
