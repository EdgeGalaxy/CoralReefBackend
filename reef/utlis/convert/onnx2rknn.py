#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project :
@File    : model_convert_rknn.py
@IDE     : PyCharm
@Author  : bhuang
@Date    : 2024/2/29 上午10:51

usage:
    1) convert onnx to fp16 rknn model:
        python model_convert_rknn.py --onnx path/to/model.onnx --platform rk3588
    2) convert onnx to int8 rknn model WITHOUT using hybrid quantization:
        python model_convert_rknn.py --onnx path/to/model.onnx --data_file path/to/dataset.txt --platform rk3588
    3) convert onnx to int8 rknn model and use hybrid quantization, but don't use accuracy analysis:
        python model_convert_rknn.py --onnx path/to/model.onnx --data_file path/to/dataset.txt --platform rk3588 --hybrid_quant
    4) convert onnx to int8 rknn model and use hybrid quantization, and use accuracy analysis:
        python model_convert_rknn.py --onnx path/to/model.onnx --data_file path/to/dataset.txt --platform rk3588 --step step1 --acc_analysis
        # based on the accuracy analysis results, manually modify the custom_quantize_layers in the xxx_model_name.quantization.cfg file
        python model_convert_rknn.py --onnx path/to/model.onnx --data_file path/to/dataset.txt --platform rk3588 --step step2
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Union
from loguru import logger
from argparse import ArgumentParser


class RKNNConversionError(Exception):
    """Base exception for RKNN conversion errors"""
    pass


class ModelLoadError(RKNNConversionError):
    """Raised when model loading fails"""
    pass


class ModelBuildError(RKNNConversionError):
    """Raised when model building fails"""
    pass


class ModelExportError(RKNNConversionError):
    """Raised when model exporting fails"""
    pass


class ConvertOnnxToRknn:
    """Convert ONNX models to RKNN format with various quantization options"""
    
    SUPPORTED_PLATFORMS = ["rk3562", "rk3566", "rk3568", "rk3588"]
    SUPPORTED_STEPS = ["onestep", "step1", "step2"]
    SUPPORTED_QUANT_ALGOS = ["normal", "mmse", "kl_divergence"]

    def __init__(
        self,
        onnx_model: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        dataset_file: Optional[str] = None,
        target_platform: str = "rk3588",
        hybrid_quant: bool = True,
        quantized_algorithm: str = "normal",
        quantized_method: str = "channel",
        optimization_level: int = 3,
        rknn_batchsize: Optional[int] = None,
        with_acc_analysis: bool = False,
        step: str = "onestep"
    ):
        if target_platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {target_platform}. Must be one of {self.SUPPORTED_PLATFORMS}")
        if step not in self.SUPPORTED_STEPS:
            raise ValueError(f"Unsupported step: {step}. Must be one of {self.SUPPORTED_STEPS}")
        if quantized_algorithm not in self.SUPPORTED_QUANT_ALGOS:
            raise ValueError(f"Unsupported quantization algorithm: {quantized_algorithm}. Must be one of {self.SUPPORTED_QUANT_ALGOS}")

        from rknn.api import RKNN

        self.onnx_model = Path(onnx_model)
        self.output_dir = Path(output_dir) if output_dir is not None else self.onnx_model.parent
        self.dataset = dataset_file
        self.target_platform = target_platform
        self.hybrid_quant = hybrid_quant
        self.quantized_algorithm = quantized_algorithm
        self.optimization_level = optimization_level
        self.do_quant = bool(dataset_file)
        self.rknn_batchsize = rknn_batchsize
        self.with_acc_analysis = with_acc_analysis
        self.step = step

        self.mean_values = [[0, 0, 0]]
        self.std_values = [[255, 255, 255]]
        self.rknn = RKNN(verbose=False)

    def convert(self) -> None:
        """Main conversion method that handles different conversion strategies"""
        try:
            if self.hybrid_quant and self.step == "onestep":
                logger.info("Starting hybrid quantization...")
                self.hybrid_quantization_step1()
                self.hybrid_quantization_step2()
            elif self.step == "onestep":
                logger.info(f"Starting normal quantization, {'using int8 quantization' if self.do_quant else 'using fp16 quantization'}")
                self._model_quantization()
            elif self.step == "step1":
                self.hybrid_quantization_step1(with_acc_analysis=self.with_acc_analysis)
            elif self.step == "step2":
                self.hybrid_quantization_step2()
            else:
                raise RKNNConversionError("Only when `hybrid_quant` is True can `step` be set to `step1` and `step2`")
        except Exception as e:
            logger.exception("Model conversion failed")
            raise e

    def _model_quantization(self) -> None:
        """Internal method to handle model quantization"""
        logger.debug("Configuring model...")
        self.rknn.config(
            mean_values=self.mean_values,
            std_values=self.std_values,
            target_platform=self.target_platform,
            optimization_level=self.optimization_level,
            quantized_algorithm=self.quantized_algorithm
        )

        logger.debug("Loading model...")
        if self.rknn.load_onnx(model=str(self.onnx_model)) != 0:
            raise ModelLoadError("Failed to load ONNX model")

        logger.debug("Building model...")
        if self.rknn.build(do_quantization=self.do_quant, dataset=self.dataset, rknn_batch_size=self.rknn_batchsize) != 0:
            raise ModelBuildError("Failed to build model")

        output_path = self.output_dir / f"{self.onnx_model.stem}.rknn"
        logger.debug(f"Exporting RKNN model to {output_path}...")
        if self.rknn.export_rknn(str(output_path)) != 0:
            raise ModelExportError("Failed to export RKNN model")
        
        logger.info(f"Successfully exported RKNN model to {output_path}")

    def hybrid_quantization_step1(self, with_acc_analysis: bool = False) -> None:
        """First step of hybrid quantization"""
        logger.debug("Configuring model for hybrid quantization step 1...")
        self.rknn.config(
            mean_values=self.mean_values,
            std_values=self.std_values,
            target_platform=self.target_platform,
            optimization_level=self.optimization_level,
            quantized_algorithm=self.quantized_algorithm
        )

        logger.debug("Loading model...")
        if self.rknn.load_onnx(model=str(self.onnx_model)) != 0:
            raise ModelLoadError("Failed to load ONNX model")

        logger.debug("Running hybrid quantization step 1...")
        if self.rknn.hybrid_quantization_step1(dataset=self.dataset, proposal=True, rknn_batch_size=self.rknn_batchsize) != 0:
            raise RKNNConversionError("Hybrid quantization step 1 failed")

        # Move generated files to output directory
        for ext in [".data", ".model", ".quantization.cfg"]:
            src = self.onnx_model.stem + ext
            dst = self.output_dir / src
            shutil.move(src, dst)
            logger.debug(f"Moved {src} to {dst}")

        if with_acc_analysis:
            self.rknn.release()
            self.rknn = RKNN(verbose=False)
            self.accuracy_analysis()

    def hybrid_quantization_step2(self) -> None:
        """Second step of hybrid quantization"""
        model_input = self.output_dir / f"{self.onnx_model.stem}.model"
        data_input = self.output_dir / f"{self.onnx_model.stem}.data"
        model_quantization_cfg = self.output_dir / f"{self.onnx_model.stem}.quantization.cfg"

        required_files = [
            (model_input, "model file"),
            (data_input, "data file"),
            (model_quantization_cfg, "quantization config file")
        ]

        for file_path, file_type in required_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Required {file_type} not found at {file_path}. Please run hybrid_quantization_step1 first.")

        logger.debug("Running hybrid quantization step 2...")
        if self.rknn.hybrid_quantization_step2(
            model_input=str(model_input),
            data_input=str(data_input),
            model_quantization_cfg=str(model_quantization_cfg)
        ) != 0:
            raise RKNNConversionError("Hybrid quantization step 2 failed")

        output_path = self.output_dir / f"{self.onnx_model.stem}.rknn"
        logger.debug(f"Exporting RKNN model to {output_path}...")
        if self.rknn.export_rknn(str(output_path)) != 0:
            raise ModelExportError("Failed to export RKNN model")
        
        logger.info(f"Successfully exported RKNN model to {output_path}")

    def accuracy_analysis(self) -> None:
        """Perform accuracy analysis on the model"""
        if not self.dataset:
            raise ValueError("Dataset file is required for accuracy analysis")

        self._model_quantization()

        with open(self.dataset) as f:
            img_path = f.readline().strip()
            if not img_path:
                raise ValueError("Unable to obtain a valid image from dataset file")

        logger.debug("Running accuracy analysis...")
        output_dir = self.output_dir / "snapshot"
        if self.rknn.accuracy_analysis(inputs=[img_path], output_dir=str(output_dir)) != 0:
            raise RKNNConversionError("Accuracy analysis failed")

        # Clean up temporary RKNN model
        temp_rknn = self.output_dir / f"{self.onnx_model.stem}.rknn"
        if temp_rknn.exists():
            temp_rknn.unlink()


def arg_parse() -> ArgumentParser:
    """Parse command line arguments"""
    parser = ArgumentParser(description="Convert ONNX model to RKNN model")
    parser.add_argument("--step", type=str, default="onestep", choices=["onestep", "step1", "step2"])
    parser.add_argument("--onnx", type=str, required=True, help="ONNX model path")
    parser.add_argument("--save_dir", type=str, default=None, help="The save directory of RKNN model")
    parser.add_argument("--data_file", type=str, default=None, help="The path of calibrate dataset (a txt file)")
    parser.add_argument("--platform", type=str, default="rk3588", choices=["rk3562", "rk3566", "rk3568", "rk3588"])
    parser.add_argument("--hybrid_quant", action="store_true", help="Using hybrid quantization")
    parser.add_argument("--quant_algo", type=str, default="normal", choices=["normal", "mmse", "kl_divergence"])
    parser.add_argument("--optimization_level", type=int, default=3, choices=[0, 1, 2, 3])
    parser.add_argument("--rknn_batchsize", type=int, default=None, help="RKNN model's batch size")
    parser.add_argument("--acc_analysis", action="store_true", help="Run accuracy analysis")
    return parser


if __name__ == '__main__':
    args = arg_parse().parse_args()
    try:
        converter = ConvertOnnxToRknn(
            onnx_model=args.onnx,
            output_dir=args.save_dir,
            dataset_file=args.data_file,
            target_platform=args.platform,
            hybrid_quant=args.hybrid_quant,
            quantized_algorithm=args.quant_algo,
            optimization_level=args.optimization_level,
            rknn_batchsize=args.rknn_batchsize,
            with_acc_analysis=args.acc_analysis,
            step=args.step
        )
        converter.convert()
    except Exception as e:
        logger.exception("RKNN conversion failed")
        raise
