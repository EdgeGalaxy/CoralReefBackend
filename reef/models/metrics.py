import json
from datetime import datetime
from typing import List, Dict, Any
from pydantic import Field
from loguru import logger
from beanie import Document, Link, TimeSeriesConfig, Granularity

from .deployments import DeploymentModel


class PipelineMetricTimeSeries(Document):
    ts: datetime = Field(description="时间戳", default_factory=datetime.now)
    deployment: Link[DeploymentModel] = Field(description="部署")
    metrics: Dict[str, Any] = Field(description="指标")

    class Settings:
        timeseries = TimeSeriesConfig(
            time_field="ts",
            granularity=Granularity.minutes,
            bucket_max_span_seconds=60,
            bucket_rounding_second=60,
            expire_after_seconds=60 * 60 * 24
        )
    
    @classmethod
    async def register_metrics(cls, deployment: DeploymentModel, metrics: Dict[str, Any]) -> None:
        logger.info(f"Register metrics: {json.dumps(metrics)}")
        # await cls(deployment=deployment, metrics=metrics).save()
    


class PipelineResultModelTimeSeries(Document):
    ts: datetime = Field(description="时间戳", default_factory=datetime.now)
    deployment: Link[DeploymentModel] = Field(description="部署")
    results: List[Dict[str, Any]] = Field(description="结果")

    class Settings:
        timeseries = TimeSeriesConfig(
            time_field="ts",
            granularity=Granularity.seconds,
            bucket_max_span_seconds=60,
            bucket_rounding_second=60,
            expire_after_seconds=60 * 60 * 24
        )
    
    @classmethod
    async def register_results(cls, deployment: DeploymentModel, results: List[Dict[str, Any]]) -> None:
        logger.info(f"Register results: {results}")
        # await cls(deployment=deployment, results=results).save()
