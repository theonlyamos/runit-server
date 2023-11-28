from ...routers.api.base import api_router
from ...routers.api.project import projects_api

api_router.include_router(projects_api)