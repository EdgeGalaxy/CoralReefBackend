from typing import List, Dict, Any, Union, Optional

import requests
from asyncer import asyncify
from loguru import logger
from inference_sdk import InferenceHTTPClient
from inference_sdk.http.utils.requests import api_key_safe_raise_for_status

from reef.config import settings

class RemotePipelineStatus:
    SUCCESS = "success"
    FAILURE = "failure"


class PipelineClient:
    def __init__(self, api_url: str, api_key: str = None):
        if api_key is None:
            api_key = settings.roboflow_api_key
        self.api_url = api_url
        self.api_key = api_key
        self.client = InferenceHTTPClient(api_url=api_url, api_key=api_key)

    @property
    async def pipeline_ids(self) -> List[str]:
        response = await asyncify(self.client.list_inference_pipelines)()
        logger.debug(f'Remote Pipeline ids: {response}')
        return [p["pipeline_id"] for p in response['fixed_pipelines']]

    async def create_pipeline(
        self,
        video_reference: Union[str, int, List[Union[str, int]]],
        workflow_spec: Dict[str, Any],
        workspace_name: str,
        output_image_fields: List[str],
        max_fps: Optional[int] = None,
        is_file_source: Optional[bool] = False
    ) -> str:
        response = await asyncify(self.client.start_inference_pipeline_with_workflow)(
            video_reference=video_reference,
            workflow_specification=workflow_spec,
            workspace_name=workspace_name,
            workflows_parameters={
                "output_image_fields": output_image_fields,
                "pipeline_name": workspace_name,
                "is_file_source": is_file_source
            },
            max_fps=max_fps,
        )
        return response['context']['pipeline_id']
    
    async def pause_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in await self.pipeline_ids:
            response = await asyncify(self.client.pause_inference_pipeline)(pipeline_id=pipeline_id) 
            state = response['status'] == RemotePipelineStatus.SUCCESS
            return state
        raise False
    
    async def resume_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in await self.pipeline_ids:
            response = await asyncify(self.client.resume_inference_pipeline)(pipeline_id=pipeline_id) 
            print(f'resume response: {response}')
            state = response['status'] == RemotePipelineStatus.SUCCESS
            return state
        raise False
    
    async def terminate_pipeline(self, pipeline_id: str) -> None:
        await asyncify(self.client.terminate_inference_pipeline)(pipeline_id=pipeline_id)
    
    async def offer_pipeline(self, pipeline_id: str, offer_request: Dict[str, Any]) -> None:
        def offer_inference_pipeline(pipeline_id: str, offer_request: Dict[str, Any], api_key: str) -> None:
            response = requests.post(
                f"{self.api_url}/inference_pipelines/{pipeline_id}/offer",
                json={"api_key": api_key, **offer_request}
            )
            api_key_safe_raise_for_status(response=response)
            return response.json()

        if pipeline_id in await self.pipeline_ids:
            return await asyncify(offer_inference_pipeline)(pipeline_id=pipeline_id, offer_request=offer_request, api_key=self.api_key)

    async def get_pipeline_metrics(self, pipeline_id: str) -> str:
        if pipeline_id not in await self.pipeline_ids:
            return {"status": "timeout", "context": {"request_id": "", "pipeline_id": pipeline_id}, "report": None}
        
        response = await asyncify(self.client.get_inference_pipeline_status)(pipeline_id=pipeline_id)
        return response
    
    async def get_pipeline_metrics_timerange(
        self,
        pipeline_id: str,
        start_time: float = None,
        end_time: float = None,
        minutes: int = 5
    ) -> Dict[str, Any]:
        """获取指定时间范围内的Pipeline指标数据"""
        def get_metrics_request(pipeline_id: str, start_time: float, end_time: float, minutes: int, api_key: str) -> Dict[str, Any]:
            params = {"minutes": minutes}
            if start_time is not None:
                params["start_time"] = start_time
            if end_time is not None:
                params["end_time"] = end_time
                
            response = requests.get(
                f"{self.api_url}/inference_pipelines/{pipeline_id}/metrics",
                params=params,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            api_key_safe_raise_for_status(response=response)
            return response.json()

        if pipeline_id not in await self.pipeline_ids:
            return {"dates": [], "datasets": []}
        
        return await asyncify(get_metrics_request)(
            pipeline_id=pipeline_id,
            start_time=start_time,
            end_time=end_time,
            minutes=minutes,
            api_key=self.api_key
        )
    
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

    async def capture_video_frame(self, video_source: Union[str, int]) -> Dict[str, Any]:
        """封装视频帧捕获接口"""
        def capture_video_frame_request(video_source: Union[str, int]) -> Dict[str, Any]:
            response = requests.post(
                f"{self.api_url}/inference_pipelines/video/capture",
                json={"video_source": video_source},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            api_key_safe_raise_for_status(response=response)
            return response.json()

        return await asyncify(capture_video_frame_request)(video_source=video_source)

    async def create_webrtc_video_stream(
        self,
        video_source: Union[str, int],
        webrtc_config: dict
    ) -> Dict[str, Any]:
        """封装WebRTC视频流创建接口"""
        def create_webrtc_stream_request(
            video_source: Union[str, int],
            webrtc_config: dict
        ) -> Dict[str, Any]:
            request_data = {
                "video_source": video_source,
                "api_key": self.api_key,
                **webrtc_config
            }
            
            response = requests.post(
                f"{self.api_url}/inference_pipelines/video/webrtc-stream",
                json=request_data,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            api_key_safe_raise_for_status(response=response)
            return response.json()

        return await asyncify(create_webrtc_stream_request)(
            video_source=video_source,
            webrtc_config=webrtc_config
        )


if __name__ == "__main__":
    import anyio

    pipeline_client = PipelineClient(api_url="http://localhost:8000", api_key="dfasdfads")
    anyio.run(pipeline_client.pipeline_ids)