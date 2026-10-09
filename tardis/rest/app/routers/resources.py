from .. import security, crud, database
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, HTTPException, Path, Security, status
from ..scopes import Resources
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel

from datetime import datetime

router = APIRouter(prefix="/resources", tags=["resources"])


class ShutdownTime(BaseModel):
    shutdown_time: datetime


@router.get("/{drone_uuid}/state", description="Get current state of a resource")
async def get_resource_state(
    drone_uuid: str = Path(..., pattern=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_resource_state(sql_registry, drone_uuid)
    try:
        query_result = query_result[0]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found"
        ) from None
    return query_result


@router.get("/", description="Get list of managed resources")
async def get_resources(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_resources(sql_registry)
    return query_result


@router.get(
    "/{remote_resource_uuid}/drone_uuid",
    description="Get drone_uuid for a given remote_resource_uuid",
)
async def get_drone_uuid(
    remote_resource_uuid: str = Path(...),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(
        security.check_basic_or_jwt_authorization, scopes=[Resources.get]
    ),
):
    query_result = await crud.get_drone_uuid(sql_registry, remote_resource_uuid)
    try:
        query_result = query_result[0]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found"
        ) from None
    return query_result


@router.patch("/{drone_uuid}/drain", description="Gently shut shown drone")
async def drain_drone(
    drone_uuid: str = Path(..., pattern=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.patch]),
):
    await crud.set_state_to_draining(sql_registry, drone_uuid)
    return {"msg": "Drone set to DrainState"}


@router.patch(
    "/{drone_uuid}/shutdown_time",
    description="Set the scheduled shutdown time of a drone",
)
async def set_shutdown_time(
    body: ShutdownTime,
    drone_uuid: str = Path(..., pattern=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.patch]),
):
    if not await crud.get_resource_state(sql_registry, drone_uuid):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found"
        )

    shutdown_time = body.shutdown_time
    if shutdown_time.tzinfo is not None:
        # TARDIS uses naive local timestamps (datetime.now()) throughout
        shutdown_time = shutdown_time.astimezone().replace(tzinfo=None)

    await crud.set_shutdown_time(sql_registry, drone_uuid, shutdown_time)
    return {"msg": f"shutdown_time set to {shutdown_time}"}
