from fastapi import APIRouter
from ...constants import API_VERSION

api_router = APIRouter(
    prefix=f"/api/{API_VERSION}"
)