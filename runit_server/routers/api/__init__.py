from ...routers.api.base import api_router
from ...routers.api.public import public_api
from ...routers.api.account import account_api
from ...routers.api.project import projects_api

api_router.include_router(public_api)
api_router.include_router(account_api)
api_router.include_router(projects_api)