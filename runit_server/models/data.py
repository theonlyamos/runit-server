from pydantic import BaseModel
from typing import Annotated, Optional

from ..constants import Language

class ProjectData(BaseModel):
    name: str
    language: Language
    description: Optional[str] = None
    github_repo: Optional[str] = None
    github_repo_branch: Optional[str] = None
    database: Optional[str] = None