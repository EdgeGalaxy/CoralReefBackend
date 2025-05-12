import json
import copy
from typing import List, Optional
from datetime import datetime
from loguru import logger

from reef.models import WorkflowTemplateModel, WorkflowModel, UserModel, WorkspaceModel
from reef.exceptions import ObjectNotFoundError
from reef.utlis.roboflow import get_roboflow_worflows
from reef.schemas.workflows import WorkflowSpecification
from reef.schemas import PaginationResponse, PaginationParams
from reef.schemas.workflow_template import TemplateResponse
from reef.templates.workflow_nodes import INPUT_NODE_TEMPLATE, STEP_NODE_TEMPLATE, OUTPUT_NODE_TEMPLATE

class WorkflowTemplate:
    def __init__(
        self,
        template: WorkflowTemplateModel
    ):
        self.template = template
    
    @classmethod
    async def get_template(cls, template_id: str) -> 'WorkflowTemplate':
        """获取模板详情"""
        template = await WorkflowTemplateModel.get(template_id, fetch_links=True)
        if not template:
            raise ObjectNotFoundError('模板不存在!')
        return cls(template=template)
    
    @classmethod
    async def sync_from_roboflow(
        cls,
        workflow_id: str,
        creator: UserModel,
        project_id: str = None,
        api_key: str = None
    ) -> 'WorkflowTemplate':
        """从 Roboflow 同步工作流为模板"""
        roboflow_workflows = await get_roboflow_worflows(workflow_id, project_id, api_key)
        logger.info(f'从Roboflow同步工作流: {project_id}/{workflow_id}')
        
        specification = json.loads(roboflow_workflows["config"])['specification']
        print(f'specification: {specification}')
        template = WorkflowTemplateModel(
            name=roboflow_workflows["name"],
            description=roboflow_workflows.get("description", ""),
            specification=specification,
            data=await cls.specification_to_workflow_data(WorkflowSpecification(**specification)),
            is_public=False,
            creator=creator,
            roboflow_id=f"{project_id}/{workflow_id}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await template.save()
        logger.info(f'同步工作流模板: {template.id}')
        return cls(template=template)

    
    @classmethod
    async def specification_to_workflow_data(cls, specification: WorkflowSpecification) -> dict:
        """Convert a specification to workflow data."""
        nodes = []
        edges = []
        
        # 添加输入节点
        input_node = copy.deepcopy(INPUT_NODE_TEMPLATE)
        input_node["data"]["formData"]["sources"] = [{"name": input["name"]} for input in specification.inputs]
        nodes.append(input_node)
        
        # 添加处理步骤节点
        for i, step in enumerate(specification.steps):
            step_node = copy.deepcopy(STEP_NODE_TEMPLATE)
            step_node["id"] = f"{step['type']}-{i}"
            step_node["position"] = {"x": 160 + i * 200, "y": 120}
            step_node["data"]["block_schema"]["properties"] = step
            step_node["data"]["manifest_type_identifier"] = step['type']
            step_node["data"]["human_friendly_block_name"] = f"{step['type']}-{i}"
            step_node["data"]["formData"] = step
            step_node["data"]["label"] = step["name"]
            nodes.append(step_node)
            
            # 添加边
            if i == 0:
                # 第一个步骤连接到输入节点
                edges.append({
                    "source": "input-node",
                    "target": step_node["id"],
                    "id": f"reactflow__edge-input-node-{step_node['id']}"
                })
            else:
                # 连接到前一个步骤
                prev_step_id = f"{specification.steps[i-1]['type']}-{i-1}"
                edges.append({
                    "source": prev_step_id,
                    "target": step_node["id"],
                    "id": f"reactflow__edge-{prev_step_id}-{step_node['id']}"
                })
        
        # 添加输出节点
        output_node = copy.deepcopy(OUTPUT_NODE_TEMPLATE)
        output_node["data"]["formData"]["params"] = [{
            "name": output["name"],
            "selector": output["selector"]
        } for output in specification.outputs]
        nodes.append(output_node)
        
        # 添加最后一个步骤到输出节点的边
        if specification.steps:
            last_step_id = f"{specification.steps[-1]['type']}-{len(specification.steps)-1}"
            edges.append({
                "source": last_step_id,
                "target": "output-node",
                "id": f"reactflow__edge-{last_step_id}-output-node"
            })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    @classmethod
    async def publish_template(
        cls,
        workflow: WorkflowModel,
        name: str,
        description: str,
        tags: List[str],
        is_public: bool = False
    ) -> 'WorkflowTemplate':
        """将工作流发布为模板"""
        template = WorkflowTemplateModel(
            name=name,
            description=description,
            specification=workflow.specification,
            data=workflow.data,
            is_public=is_public,
            creator=workflow.creator,
            tags=tags,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await template.save()
        logger.info(f'发布工作流模板: {template.id}')
        return cls(template=template)
    
    @classmethod
    async def list_templates(
        cls,
        is_public: Optional[bool] = None,
        creator: Optional[UserModel] = None,
        pagination: Optional[PaginationParams] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = True
    ) -> PaginationResponse[TemplateResponse]:
        """获取模板列表"""
        find_query = WorkflowTemplateModel.find(fetch_links=True)
        if is_public is not None:
            find_query = WorkflowTemplateModel.find(WorkflowTemplateModel.is_public == is_public, fetch_links=True)
        if creator:
            find_query = find_query.find(WorkflowTemplateModel.creator.id == creator.id, fetch_links=True)
        
        # 计算总记录数
        total = await find_query.count()
        
        # 添加排序
        if sort_by:
            find_query = find_query.sort(
                (sort_by, -1) if sort_desc else (sort_by, 1)
            )
        else:
            # 默认按创建时间倒序
            find_query = find_query.sort("-created_at")
        
        # 如果提供了分页参数，则应用分页
        if pagination:
            total_pages = (total + pagination.page_size - 1) // pagination.page_size
            skip = (pagination.page - 1) * pagination.page_size
            find_query = find_query.skip(skip).limit(pagination.page_size)
            templates = await find_query.to_list()
            
            return PaginationResponse(
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                items=[TemplateResponse.db_to_schema(template) for template in templates]
            )
        else:
            # 如果没有分页参数，返回所有记录
            templates = await find_query.to_list()
            return PaginationResponse(
                total=total,
                page=1,
                page_size=total,
                total_pages=1,
                items=[TemplateResponse.db_to_schema(template) for template in templates]
            )
    
    async def update_template(self, template_data: dict) -> None:
        """更新模板信息"""
        for key, value in template_data.items():
            setattr(self.template, key, value)
        
        self.template.updated_at = datetime.now()
        await self.template.save()
    
    async def toggle_visibility(self) -> None:
        """切换模板可见性"""
        self.template.is_public = not self.template.is_public
        self.template.updated_at = datetime.now()
        await self.template.save()
    
    async def delete_template(self) -> None:
        """删除模板"""
        await self.template.delete()
        logger.info(f'删除工作流模板: {self.template.id}')
    
    async def fork_to_workspace(self, target_workspace: WorkspaceModel) -> WorkflowModel:
        """将模板复制到目标工作空间"""
        workflow = WorkflowModel(
            name=f"copy_{self.template.name}",
            description=self.template.description,
            specification=self.template.specification,
            data=self.template.data,
            workspace=target_workspace,
            creator=target_workspace.owner_user,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await workflow.save()
        
        # 更新使用次数
        self.template.usage_count += 1
        await self.template.save()
        
        logger.info(f'复制模板到工作空间: {workflow.id}')
        return workflow