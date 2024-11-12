from datetime import datetime
from typing import List
from loguru import logger

from reef.models import (
    UserModel,
    WorkspaceModel,
    WorkspaceUserModel,
    WorkspaceRole
)

from reef.exceptions import ValidationError

class WorkspaceCore:
    def __init__(
        self,
        workspace: WorkspaceModel
    ):
        self.workspace = workspace

    @classmethod
    async def create_workspace(cls, user: UserModel, workspace_data: dict) -> 'WorkspaceCore':
        """Create a new workspace owned by the given user"""
        workspace = WorkspaceModel(
            **workspace_data,
            owner_user=user,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await workspace.insert()
        
        # Create workspace user relationship with admin role
        workspace_user = WorkspaceUserModel(
            user=user,
            workspace=workspace,
            role=WorkspaceRole.ADMIN,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await workspace_user.insert()
        
        logger.info(f'用户 {user.id} 创建工作空间: {workspace.id}')
        return cls(workspace=workspace)

    async def add_user(self, owner_user: UserModel, invited_user: UserModel, role: WorkspaceRole) -> None:
        """Add user to workspace with specified role"""
        # Check if user is already in workspace
        existing = await WorkspaceUserModel.find_one(
            WorkspaceUserModel.user.id == invited_user.id,
            WorkspaceUserModel.workspace.id == self.workspace.id
        )
        
        if existing:
            raise ValidationError('用户已在工作空间中!')
        
        if owner_user.id != self.workspace.owner_user.id:
            raise ValidationError('只有工作空间所有者才能添加用户!')
            
        # Check workspace user limit
        current_users = await WorkspaceUserModel.find(
            WorkspaceUserModel.workspace.id == self.workspace.id
        ).count()
        
        if current_users >= self.workspace.max_users:
            raise ValidationError('工作空间用户数已达上限!')
            
        workspace_user = WorkspaceUserModel(
            user=invited_user,
            workspace=self.workspace,
            role=role,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await workspace_user.insert()
        logger.info(f'用户 {invited_user.id} 加入工作空间: {self.workspace.id}')

    async def remove_user(self, user: UserModel) -> None:
        """Remove user from workspace"""
        # Cannot leave if user is workspace owner
        if self.workspace.owner_user.id == user.id:
            raise ValidationError(f'工作空间所有者无法退出工作空间!')
        
        if user != self.workspace.owner_user:
            raise ValidationError(f'只有工作空间所有者才能删除用户!')
            
        result = await WorkspaceUserModel.find_one(
            WorkspaceUserModel.user.id == user.id,
            WorkspaceUserModel.workspace.id == self.workspace.id
        ).delete()
        
        if result:
            logger.info(f'用户 {user.id} 退出工作空间: {self.workspace.id}')

    @staticmethod
    async def get_user_workspaces(user: UserModel, is_admin: bool = False) -> List[WorkspaceModel]:
        """Get all workspaces for a user"""
        workspace_users = await WorkspaceUserModel.find(
            WorkspaceUserModel.user.id == user.id,
            fetch_links=True
        ).to_list()
        
        if is_admin:
            workspace_users = [wu for wu in workspace_users if wu.role == WorkspaceRole.ADMIN]
        
        return [wu.workspace for wu in workspace_users]
