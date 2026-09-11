---
name: fastapi-best-practices
description: >-
  Production-grade FastAPI development guide, API structure, Pydantic v2 validation,
  dependency injection, CORS middleware, security, and async endpoint optimization.
---

# FastAPI Best Practices & Design Patterns

This skill provides comprehensive instructions for designing scalable, type-safe, and high-performance RESTful APIs with FastAPI.

---

## 1. Project Structure & Layer Separation

```text
app/
├── main.py              # Application entrypoint & middleware configuration
├── api/                 # API route handlers (endpoints)
│   ├── v1/
│   │   ├── auth.py
│   │   ├── cursos.py
│   │   └── actividades.py
│   └── router.py
├── core/                # Core config, security & database session
│   ├── config.py
│   └── security.py
├── schemas/             # Pydantic data validation schemas
│   └── curso.py
├── services/            # Business domain logic
│   └── curso_service.py
```

---

## 2. Type-Safe Pydantic v2 Schemas

```python
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List

class CursoBase(BaseModel):
    id: str = Field(..., description="ID único de la materia")
    nombre: str = Field(..., min_length=2, description="Nombre de la asignatura")
    favorito: bool = False

class CursoResponse(CursoBase):
    model_config = ConfigDict(from_attributes=True)
    avance: Optional[int] = Field(default=None, ge=0, le=100)
    ultimo_acceso: Optional[str] = None
```

---

## 3. Dependency Injection & Router Setup

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

router = APIRouter(prefix="/cursos", tags=["Cursos"])

def get_current_user_token(authorization: str = None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorización requerido"
        )
    return authorization

@router.get("/", response_model=List[CursoResponse])
async def list_cursos(token: str = Depends(get_current_user_token)):
    """Devuelve la lista de cursos del usuario autenticado."""
    return [{"id": "101", "nombre": "Programación I", "avance": 80}]
```

---

## 4. Middleware & CORS Configuration

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API Campus Virtual IES N°5",
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
