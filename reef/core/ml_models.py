import json
from typing import List, Optional
from datetime import datetime

from loguru import logger

from beanie.odm.operators.find.logical import Or
from inference_sdk.http.utils.aliases import resolve_roboflow_model_alias

from reef.models import (
    MLModelModel,
    WorkspaceModel,
    Environment,
    MLPlatform,
    MLTaskType,
    DatasetType
)
from reef.schemas.ml_models import MLModelCreate 
from reef.exceptions import ValidationError
from reef.utlis.roboflow import get_roboflow_model_data, get_roboflow_model_ids, get_models_type
from reef.utlis.cloud import upload_data_to_cloud, transfer_object


class MLModelCore:
    def __init__(
        self,
        model: MLModelModel
    ):
        self.model = model

    @classmethod
    async def get_workspace_models(cls, workspace: WorkspaceModel) -> List[MLModelModel]:
        """Get all ML models for this workspace."""
        return await MLModelModel.find(
            Or(
                MLModelModel.workspace.id == workspace.id,
                MLModelModel.is_public == True
            ),
            fetch_links=True
        ).sort("-created_at").to_list()
    
    @classmethod
    async def get_public_models(cls) -> List[MLModelModel]:
        return await MLModelModel.find(
            MLModelModel.is_public == True,
            fetch_links=True
        ).sort("-created_at").to_list()
    
    @classmethod
    async def get_model_by_id(cls, model_id: str) -> 'MLModelCore':
        model = await MLModelModel.find_one(
            MLModelModel.name == model_id
        )
        if not model:
            return await cls.register_roboflow_model(model_id)
        return cls(model=model)
    
    @classmethod
    async def get_model_by_model_alias(cls, model_alias: str) -> 'MLModelCore':
        model = await MLModelModel.find_one(
            MLModelModel.version == model_alias
        )
        return cls(model=model)

    @classmethod
    async def register_custom_model(
        cls,
        data: MLModelCreate,
        workspace: WorkspaceModel,
    ) -> 'MLModelCore':
        """Create a new ML model."""
        environment = Environment(
            PREPROCESSING=json.dumps(data.preprocessing_config.model_dump()),
            CLASS_MAP=data.class_mapping,
            COLORS=data.class_colors,
            BATCH_SIZE=data.batch_size
        )
        model_alias = await MLModelModel.pick_new_dataset_version(data.dataset_type)
        onnx_model_key = f"{model_alias}/weights.onnx"
        rknn_model_key = f"{model_alias}/weights.rknn"
        await transfer_object(data.onnx_model_url, onnx_model_key)
        if data.rknn_model_url:
            await transfer_object(data.rknn_model_url, rknn_model_key)
            
        environment_key = await upload_data_to_cloud(
            data=environment.model_dump_json(), 
            key=f"{model_alias}/environment.json"
        )
        model = MLModelModel(
            name=f"custom-{data.name}-{model_alias.split('/')[-1]}",
            description=data.description,
            platform=data.platform,
            dataset_url=data.dataset_url,
            dataset_type=data.dataset_type,
            task_type=data.task_type,
            model_type=data.model_type,
            onnx_model_url=onnx_model_key,
            rknn_model_url=rknn_model_key,
            environment=environment,
            environment_url=environment_key,
            version=model_alias,
            workspace=workspace,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await model.insert()
        logger.info(f'Created ML model: {model.id}')
        return cls(model=model)
    
    @classmethod
    async def register_roboflow_model(
        cls,
        model_id: str,
    ) -> 'MLModelCore':
        api_data = await get_roboflow_model_data(model_id)
        model_alias = resolve_roboflow_model_alias(model_id)
        dataset_type = DatasetType(model_alias.split("/")[0])

        model = MLModelModel(
            name=model_id,
            description=f"dataset version {model_alias} for {api_data['type']}",
            platform=MLPlatform.ROBOFLOW,
            dataset_type=dataset_type,
            task_type=MLTaskType(api_data["type"]),
            model_type=api_data["modelType"],
            onnx_model_url=api_data["model"],
            rknn_model_url=None,
            environment=api_data["environment"],
            environment_url=api_data["environment_key"],
            version=model_alias,
            is_public=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await model.insert()
        logger.info(f'Created ML model: {model.id}')
        return cls(model=model)
    
    @classmethod
    async def get_roboflow_model_ids(cls) -> List[str]:
        return await get_roboflow_model_ids()
    
    @classmethod
    async def get_models_type(cls) -> List[str]:
        return await get_models_type()

    async def update_model(self, model_data: dict) -> None:
        """Update an existing ML model."""
        for key, value in model_data.items():
            setattr(self.model, key, value)
        
        self.model.updated_at = datetime.now()
        await self.model.save()
        logger.info(f'Updated ML model: {self.model.id}')

    async def delete_model(self) -> None:
        """Delete an ML model and check related deployments."""
        # TODO: 检查模型是否被部署使用
        
        await self.model.delete()
        logger.info(f'Deleted ML model: {self.model.id}')
    
    async def convert_onnx_to_rknn(self) -> None:
        """Convert ONNX model to RKNN model."""
        pass
