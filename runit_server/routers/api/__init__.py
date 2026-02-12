from ...routers.api.base import api_router
from ...routers.api.public import public_api
from ...routers.api.account import account_api
from ...routers.api.project import projects_api
from ...routers.api.database import database_api

# Specific prefixes first (account, projects, database) so they don't get
# captured by public_api's catch-all /{project_id} routes
api_router.include_router(account_api)
api_router.include_router(projects_api)
api_router.include_router(database_api)
api_router.include_router(public_api)