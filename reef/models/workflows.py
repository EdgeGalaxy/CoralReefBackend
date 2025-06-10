from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pydantic import Field
from beanie import Document, Link
from .workspaces import WorkspaceModel
from .users import UserModel



class WorkflowModel(Document):
    name: str = Field(description="工作流名称")
    description: str = Field(description="工作流描述")
    roboflow_id: Optional[str] = Field(default=None, description="Roboflow ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="工作流数据")
    specification: Dict[str, Any] = Field(description="工作流定义")
    specification_md5: Optional[str] = Field(default=None, description="specification 的 md5")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")
    creator: Link[UserModel] = Field(description="创建者")

    class Settings:
        name = "workflows"

    async def get_output_image_fields(self) -> List[str]:
        """Get the output image fields of the workflow."""
        def _extract_image_fields_from_node(node: Dict[str, Any]) -> Optional[Tuple[str, str]]:
            """从节点中提取图像字段信息
            
            Args:
                node: 工作流节点数据
                
            Returns:
                节点名称和对应的图像字段名称的元组,如果没有图像字段则返回 None
            """
            node_name = node["data"]["formData"].get("name", "")
            for output in node["data"].get("outputs_manifest", []):
                for kind_item in output.get("kind", []):
                    if node_name and kind_item.get("internal_data_type") == "WorkflowImageData":
                        return node_name, output["name"]
            return None
            
        def _build_image_fields_mapper() -> Dict[str, str]:
            """构建节点名称到图像字段的映射
            
            Returns:
                节点名称到图像字段名称的映射字典
            """
            mapper = {}
            for node in self.data["nodes"]:
                result = _extract_image_fields_from_node(node)
                if result:
                    node_name, field_name = result
                    mapper[node_name] = field_name
            return mapper
            
        output_image_fields = []
        image_fields_mapper = _build_image_fields_mapper()
        selectors = {output["name"]: output["selector"].split(".") for output in self.specification["outputs"]}
        for output_name, selector in selectors.items():
            _, node_name, field_name = selector
            if image_fields_mapper.get(node_name, "") == field_name:
                output_image_fields.append(output_name)
        return output_image_fields