from enum import Enum
from typing import List, Dict, Any, Union

from asyncer import asyncify
from inference_sdk import InferenceHTTPClient


class RemotePipelineStatus:
    SUCCESS = "success"
    FAILURE = "failure"


class PipelineClient:
    def __init__(self, api_url: str, api_key: str = None):
        self.client = InferenceHTTPClient(api_url=api_url, api_key='jDmVpLRLlwVHOafDapSi')

    @property
    async def pipeline_ids(self) -> List[str]:
        response = await asyncify(self.client.list_inference_pipelines)()
        print('response', response)
        return [p for p in response['pipelines']]

    async def create_pipeline(
        self,
        video_reference: Union[str, int, List[Union[str, int]]],
        workflow_spec: Dict[str, Any],
        workspace_name: str
    ) -> str:
        response = await asyncify(self.client.start_inference_pipeline_with_workflow)(
            video_reference=video_reference,
            workflow_specification=workflow_spec,
            workspace_name=workspace_name
        )
        return response['context']['pipeline_id']
    
    async def pause_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in await self.pipeline_ids:
            response = await asyncify(self.client.pause_inference_pipeline)(pipeline_id=pipeline_id) 
            return response['status'] == RemotePipelineStatus.SUCCESS
        raise False
    
    async def resume_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in await self.pipeline_ids:
            response = await asyncify(self.client.resume_inference_pipeline)(pipeline_id=pipeline_id) 
            return response['status'] == RemotePipelineStatus.SUCCESS
        raise False

    async def terminate_pipeline(self, pipeline_id: str) -> None:
        if pipeline_id in await self.pipeline_ids:
            await asyncify(self.client.terminate_inference_pipeline)(pipeline_id=pipeline_id)

    async def get_pipeline_metrics(self, pipeline_id: str) -> str:
        if pipeline_id not in await self.pipeline_ids:
            return {"status": "timeout", "context": {"request_id": "", "pipeline_id": pipeline_id}, "report": None}
        
        response = await asyncify(self.client.get_inference_pipeline_status)(pipeline_id=pipeline_id)
        return response
    
    async def get_pipeline_results(
        self,
        pipeline_id: str,
        exclude_fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        response = await asyncify(self.client.consume_inference_pipeline_result)(
            pipeline_id=pipeline_id,
            excluded_fields=exclude_fields
        )
        return response


if __name__ == "__main__":
    import anyio

    pipeline_client = PipelineClient(api_url="http://localhost:8000", api_key="dfasdfads")
    anyio.run(pipeline_client.pipeline_ids)