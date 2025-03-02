from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from pydantic import model_validator
from reef.models.workflows import WorkflowModel
from reef.exceptions import ValidationError

class InputParamsType(str, Enum):
    workflow_image = "WorkflowImage"
    workflow_parameter = "WorkflowParameter"

class WorkflowSpecification(BaseModel):
    version: str = Field(description="工作流版本")
    inputs: List[Dict[str, Any]] = Field(description="工作流输入")
    steps: List[Dict[str, Any]] = Field(description="工作流步骤")
    outputs: List[Dict[str, Any]] = Field(description="工作流输出")

class WorkflowData(BaseModel):
    nodes: List[Dict[str, Any]] = Field(description="节点数据")
    edges: List[Dict[str, Any]] = Field(description="边数据")


class WorkflowBase(BaseModel):
    name: Optional[str] = Field(default=None, description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    specification: Optional[WorkflowSpecification] = Field(default=None, description="工作流定义")
    data: Optional[WorkflowData] = Field(default=None, description="工作流数据")

    @model_validator(mode='after')
    def validate_data(self):
        if self.data is None and self.specification is None:
            raise ValidationError("参数data和specification不能同时为空!")
        if self.data is None:
            return self
        self.specification = self.make_specification(self.data)
        return self
    
    @classmethod
    def make_specification(cls, data: Optional[WorkflowData] = None):
        if data is None:
            return {}
        inputs, steps, outputs = [], [], []
        for node in data.nodes:
            if node["data"]["manifest_type_identifier"] == "input":
                inputs.extend(cls._handle_input_node(node))
            elif node["data"]["manifest_type_identifier"] == "output":
                outputs.extend(cls._handle_output_node(node))
            else:
                steps.append(node["data"]["formData"])
        return WorkflowSpecification(
            version="v1",
            inputs=inputs,
            steps=steps,
            outputs=outputs,
        )

    @classmethod
    def _handle_input_node(cls, node: Dict[str, Any]):
        inputs = []
        # Handle list of form data for input type
        form_data = node["data"]["formData"]
        images = form_data.get("images", [])
        params = form_data.get("params", [])
            
        for image in images:
            inputs.append({
                "name": image["name"],
                "type": InputParamsType.workflow_image.value,
            })
        for param in params:
            inputs.append({
                "name": param["name"],
                "type": InputParamsType.workflow_parameter.value,
                "default_value": param["value"],
            })
        return inputs

    @classmethod
    def _handle_output_node(cls, node: Dict[str, Any]):
        outputs = []
        form_data = node["data"]["formData"]["params"]
        for output in form_data:
            outputs.append({
                "type": "JsonField",
                "name": output["name"],
                "selector": output["selector"],
            })
        return outputs

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowUpdate(WorkflowBase):
    pass

class WorkflowRename(BaseModel):
    name: str
    description: Optional[str] = Field(default=None, description="工作流描述")

class WorkflowResponse(WorkflowBase):
    id: str
    created_at: datetime
    updated_at: datetime
    workspace_id: str
    workspace_name: str

    @classmethod
    def db_to_schema(cls, workflow: WorkflowModel):
        return cls(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            data=workflow.data,
            specification=workflow.specification,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            workspace_id=str(workflow.workspace.id),
            workspace_name=workflow.workspace.name,
        )
