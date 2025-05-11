from datetime import datetime
from typing import List, Optional, Tuple
from loguru import logger

from reef.models import (
    UserModel,
    WorkspaceModel,
    WorkspaceUserModel,
    WorkspaceRole,
    GatewayModel
)
from reef.schemas.workspaces import WorkspaceDetailResponse, WorkspaceUsers
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
        
        result = await WorkspaceUserModel.find_one(
            WorkspaceUserModel.user.id == user.id,
            WorkspaceUserModel.workspace.id == self.workspace.id
        ).delete()
        
        if result:
            logger.info(f'用户 {user.id} 退出工作空间: {self.workspace.id}')

    @classmethod
    async def get_user_workspaces(
        cls,
        user: UserModel,
        with_users: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Tuple[List[WorkspaceDetailResponse], int]:
        """获取用户的工作空间列表，包含每个工作空间的用户数量和当前用户角色
        
        Args:
            user: 用户模型
            skip: 跳过的记录数
            limit: 返回的记录数
            
        Returns:
            Tuple[List[dict], int]: 包含工作空间信息的字典列表和总数，每个字典包含:
                - workspace: 工作空间信息
                - user_count: 该工作空间的用户数量
                - current_user_role: 当前用户在该工作空间的角色
        """
        user_workspaces = WorkspaceUserModel.find(
            WorkspaceUserModel.user.id == user.id,
            fetch_links=True,
            sort='-created_at'
        )

        total = await user_workspaces.count()

        if skip is not None:
            user_workspaces = user_workspaces.skip(skip)
        if limit is not None:
            user_workspaces = user_workspaces.limit(limit)
        
        result = []
        
        for uw in await user_workspaces.to_list():
            users = await WorkspaceUserModel.find(
                WorkspaceUserModel.workspace.id == uw.workspace.id,
                fetch_links=True
            ).to_list() if with_users else []
            row = WorkspaceDetailResponse(
                id=str(uw.workspace.id),
                name=uw.workspace.name,
                description=uw.workspace.description,
                max_users=uw.workspace.max_users,
                owner_user_id=str(uw.workspace.owner_user.id),
                user_count=await WorkspaceUserModel.find(
                    WorkspaceUserModel.workspace.id == uw.workspace.id
                ).count(),
                current_user_role=uw.role,
                created_at=uw.workspace.created_at,
                updated_at=uw.workspace.updated_at,
                users=[
                    WorkspaceUsers(
                        id=str(user.user.id),
                        username=user.user.username,
                        email=user.user.email,
                        role=user.role,
                        join_at=user.created_at
                    )
                    for user in users
                ]
            )
            result.append(row)
            
        return result, total

    async def update_workspace(self, user: UserModel, workspace_data: dict) -> None:
        """Update workspace information
        
        Args:
            user: User model requesting the update
            workspace_data: Dict containing workspace data to update
        
        Raises:
            ValidationError: If user is not the workspace owner
        """
        # 验证用户是否为工作空间所有者
        if str(self.workspace.owner_user.id) != str(user.id):
            raise ValidationError("只有工作空间所有者才能更新工作空间信息")
        
        # 更新允许的字段
        allowed_fields = ["name", "description", "max_users"]
        update_data = {k: v for k, v in workspace_data.items() if k in allowed_fields}
        
        # 添加更新时间
        update_data["updated_at"] = datetime.now()
        
        # 更新工作空间
        await self.workspace.update({"$set": update_data})
        logger.info(f"用户 {user.id} 更新工作空间 {self.workspace.id}")
    
    async def delete_workspace(self, user: UserModel) -> None:
        """Delete workspace if no gateways are associated with it
        
        Args:
            user: User model requesting the deletion
            
        Raises:
            ValidationError: If user is not the workspace owner or if gateways exist
        """
        # 验证用户是否为工作空间所有者
        if str(self.workspace.owner_user.id) != str(user.id):
            raise ValidationError("只有工作空间所有者才能删除工作空间")
        
        # 检查是否存在关联的网关
        gateways_count = await GatewayModel.find(
            GatewayModel.workspace.id == self.workspace.id
        ).count()
        
        if gateways_count > 0:
            raise ValidationError("工作空间存在关联的网关，无法删除")

        # 检查是否是用户的唯一工作空间
        user_workspaces_count = await WorkspaceUserModel.find(
            WorkspaceUserModel.user.id == user.id
        ).count()
        
        if user_workspaces_count <= 1:
            raise ValidationError("不能删除用户的唯一工作空间")
        
        # 删除所有工作空间用户关联
        await WorkspaceUserModel.find(
            WorkspaceUserModel.workspace.id == self.workspace.id
        ).delete()
        
        # 删除工作空间
        await self.workspace.delete()
        logger.info(f"用户 {user.id} 删除工作空间 {self.workspace.id}")
