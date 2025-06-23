from fastapi import APIRouter, Depends

from reef.api._depends import get_workspace
from reef.core.statics import StatisticsCore
from reef.models import WorkspaceModel

router = APIRouter(tags=['statistics'], prefix='/workspace/{workspace_id}/statics')


@router.get('/')
async def get_full_statistics(
    workspace: WorkspaceModel = Depends(get_workspace),
):
    """
    Get all statistics for the current workspace.
    """
    return await StatisticsCore.get_full_workspace_statistics(workspace) 