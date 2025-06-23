from datetime import datetime
from typing import Any, Dict

from reef.models import (
    CameraModel,
    DeploymentModel,
    GatewayModel,
    GatewayStatus,
    WorkspaceModel,
    OperationStatus
)


class StatisticsCore:
    @classmethod
    async def get_workspace_overview(cls, workspace: WorkspaceModel) -> Dict[str, Any]:
        """Get overview statistics for a workspace."""

        gateways_count = await GatewayModel.find(
            GatewayModel.workspace.id == workspace.id,
            GatewayModel.status != GatewayStatus.DELETED,
        ).count()

        cameras_count = await CameraModel.find(
            CameraModel.workspace.id == workspace.id,
        ).count()

        deployments_count = await DeploymentModel.find(
            DeploymentModel.workspace.id == workspace.id,
        ).count()

        # Get running deployments count
        running_deployments = await DeploymentModel.find(
            DeploymentModel.workspace.id == workspace.id,
            DeploymentModel.running_status == OperationStatus.RUNNING,
        ).count()

        return {
            'gateways': gateways_count,
            'cameras': cameras_count,
            'deployments': deployments_count,
            'running_deployments': running_deployments,
        }

    @classmethod
    async def get_full_workspace_statistics(cls, workspace: WorkspaceModel) -> Dict[str, Any]:
        """Get all statistics for a workspace."""
        overview = await cls.get_workspace_overview(workspace)
        deployments_by_status = await cls.get_deployments_by_status(workspace)
        gateways_by_status = await cls.get_gateways_by_status(workspace)

        return {
            "overview": overview,
            "deployments_by_status": deployments_by_status,
            "gateways_by_status": gateways_by_status,
        }

    @classmethod
    async def get_deployments_by_status(cls, workspace: WorkspaceModel) -> Dict[str, int]:
        """Get deployment count by status."""
        pipeline = [
            {'$match': {'workspace.$id': workspace.id}},
            {'$group': {'_id': '$running_status', 'count': {'$sum': 1}}},
        ]
        results = await DeploymentModel.aggregate(pipeline).to_list()

        # Initialize all possible statuses with 0
        status_counts = {status: 0 for status in OperationStatus}
        # Update with actual counts
        for item in results:
            if item['_id'] in status_counts:
                status_counts[item['_id']] = item['count']

        return status_counts

    @classmethod
    async def get_gateways_by_status(cls, workspace: WorkspaceModel) -> Dict[str, int]:
        """Get gateway count by status."""
        # Not counting DELETED ones.
        pipeline = [
            {
                '$match': {
                    'workspace.$id': workspace.id,
                    'status': {'$ne': GatewayStatus.DELETED},
                }
            },
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
        ]
        results = await GatewayModel.aggregate(pipeline).to_list()
        return {item['_id']: item['count'] for item in results} 