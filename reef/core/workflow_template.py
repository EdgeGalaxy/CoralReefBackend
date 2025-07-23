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
from reef.utlis.roboflow import get_block_by_identifier

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
        input_node["data"]["formData"]["sources"] = [{"name": "image"}]
        input_node["data"]["formData"]["params"] = [{"name": step['name'], "value": step['default_value']} for step in specification.inputs if step['type'] == 'WorkflowParameter']
        nodes.append(input_node)
        
        # 创建步骤名称到索引的映射
        step_name_to_index = {step['name']: i for i, step in enumerate(specification.steps)}
        
        # 添加处理步骤节点
        for i, step in enumerate(specification.steps):
            step_node = copy.deepcopy(STEP_NODE_TEMPLATE)
            step_node["id"] = f"{step['type']}-{i}"
            step_node["position"] = {"x": 160 + i * 200, "y": 120 + i * 100}
            step_node["data"] = await get_block_by_identifier(step['type'])
            step_node["data"]["formData"] = step
            nodes.append(step_node)
        
        # 基于依赖关系构建边 - 每个节点只连接最近的上游节点
        for i, step in enumerate(specification.steps):
            step_id = f"{step['type']}-{i}"
            dependencies = cls._extract_step_dependencies(step)
            
            # 找到最近的上游节点
            closest_upstream = None
            max_upstream_index = -1
            
            # 检查对其他步骤的依赖，找到索引最大的（最近的）
            for dep_step_name in dependencies:
                if dep_step_name in step_name_to_index:
                    dep_index = step_name_to_index[dep_step_name]
                    if dep_index > max_upstream_index:
                        max_upstream_index = dep_index
                        closest_upstream = f"{specification.steps[dep_index]['type']}-{dep_index}"
            
            # 如果有最近的上游步骤，连接到它
            if closest_upstream:
                edges.append({
                    "source": closest_upstream,
                    "target": step_id,
                    "id": f"reactflow__edge-{closest_upstream}-{step_id}"
                })
            # 否则检查是否需要连接到输入节点
            elif cls._has_input_dependency(step):
                edges.append({
                    "source": "input-node",
                    "target": step_id,
                    "id": f"reactflow__edge-input-node-{step_id}"
                })
            # 如果没有任何依赖，连接到前一个步骤（保持线性）
            elif i > 0:
                prev_step_id = f"{specification.steps[i-1]['type']}-{i-1}"
                edges.append({
                    "source": prev_step_id,
                    "target": step_id,
                    "id": f"reactflow__edge-{prev_step_id}-{step_id}"
                })
            # 第一个步骤且没有依赖，连接到输入
            else:
                edges.append({
                    "source": "input-node",
                    "target": step_id,
                    "id": f"reactflow__edge-input-node-{step_id}"
                })
        
        # 添加输出节点
        output_node = copy.deepcopy(OUTPUT_NODE_TEMPLATE)
        output_node["data"]["formData"]["params"] = [{
            "name": output["name"],
            "selector": output["selector"],
            "value": output["selector"]
        } for output in specification.outputs]
        nodes.append(output_node)
        
        # 连接输出依赖的步骤到输出节点 - 只连接没有下游节点的步骤
        output_dependencies = set()
        for output in specification.outputs:
            if output["selector"].startswith("$steps."):
                step_name = output["selector"].split(".")[1]
                if step_name in step_name_to_index:
                    output_dependencies.add(step_name)
        
        # 找出所有作为上游节点的步骤（有下游节点的步骤）
        steps_with_downstream = set()
        for i, step in enumerate(specification.steps):
            dependencies = cls._extract_step_dependencies(step)
            steps_with_downstream.update(dependencies)
        
        # 只连接输出依赖中没有下游节点的步骤
        for dep_step_name in output_dependencies:
            if dep_step_name not in steps_with_downstream:
                dep_index = step_name_to_index[dep_step_name]
                source_id = f"{specification.steps[dep_index]['type']}-{dep_index}"
                edges.append({
                    "source": source_id,
                    "target": "output-node",
                    "id": f"reactflow__edge-{source_id}-output-node"
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    @classmethod
    def _extract_step_dependencies(cls, step: dict) -> set:
        """提取步骤中对其他步骤的依赖"""
        import re
        dependencies = set()
        
        def extract_from_value(value):
            if isinstance(value, str) and "$steps." in value:
                # 更精确的正则表达式，匹配 $steps.step_name.property 格式
                matches = re.findall(r'\$steps\.([^.\s\[\]]+)(?:\.[^.\s\[\]]+)*', value)
                dependencies.update(matches)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)
        
        # 递归提取所有字段中的依赖
        for key, value in step.items():
            if key != 'name' and key != 'type':  # 排除名称和类型字段
                extract_from_value(value)
        
        return dependencies
    
    @classmethod
    def _has_input_dependency(cls, step: dict) -> bool:
        """检查步骤是否依赖输入"""
        
        def check_value(value):
            if isinstance(value, str) and "$inputs." in value:
                return True
            elif isinstance(value, dict):
                return any(check_value(v) for v in value.values())
            elif isinstance(value, list):
                return any(check_value(item) for item in value)
            return False
        
        # 检查所有字段是否包含输入依赖
        for key, value in step.items():
            if key != 'name' and key != 'type':  # 排除名称和类型字段
                if check_value(value):
                    return True
        
        return False
    
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