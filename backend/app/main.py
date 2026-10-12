import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.catalog import router as catalog_router
from app.api.variants import router as variants_router
from app.api.knowledge import router as knowledge_router
from app.api.practice import router as practice_router
from app.api.market_insights import router as market_insights_router
from app.api.agenda import router as agenda_router
from app.api.squad_safety import router as squad_safety_router
from app.api.dcp_filters import router as dcp_filters_router
from app.api.objective_planning import router as objective_planning_router
from app.api.planner import router as planner_router
from app.api.connections import router as connections_router
from app.api.routes import router
from app.api.emulator import router as emulator_router
from app.api.emulator import recover_interrupted_automation
from app.api.analysis import router as analysis_router
from app.api.fc27 import router as fc27_router
from app.core.config import settings
from app.services.locks import ResourceBusy
from starlette.concurrency import run_in_threadpool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_in_threadpool(recover_interrupted_automation)
    from app.services.providers import recover_reads
    await run_in_threadpool(recover_reads)
    yield

app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan, docs_url="/docs", redoc_url=None, root_path="/api")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token", "X-App-Entry"])

@app.get('/build', tags=['Estado local'])
def build_metadata():
    from app.core.build import build_info
    return build_info()

@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    from app.services.spanish import validation_message
    return JSONResponse(status_code=422, content={"detail": "Datos de entrada inválidos", "errors": [{"field": ".".join(map(str, e["loc"])), "message": validation_message(e)} for e in exc.errors()]})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger("api").exception("Error no controlado en %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Ocurrió un error interno. Revisa los registros locales."})

@app.exception_handler(ResourceBusy)
async def busy_resource(_: Request, exc: ResourceBusy):
    return JSONResponse(status_code=409, content={"detail": "Otra operación utiliza este recurso. Espera a que termine y vuelve a intentarlo."})

app.include_router(router)
app.include_router(emulator_router)
app.include_router(analysis_router)
app.include_router(squad_safety_router)
app.include_router(dcp_filters_router)
app.include_router(objective_planning_router)
app.include_router(fc27_router)

app.include_router(connections_router)

@app.middleware("http")
async def private_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response

app.include_router(planner_router)

app.include_router(knowledge_router)
app.include_router(practice_router)
app.include_router(market_insights_router)
app.include_router(agenda_router)

app.include_router(catalog_router)
app.include_router(variants_router)
