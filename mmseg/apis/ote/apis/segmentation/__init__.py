# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

from .config_utils import (patch_config,
                           set_hyperparams)
from .configuration import OTESegmentationConfig
from .openvino_task import OpenVINOSegmentationTask

from .inference_task import OTESegmentationInferenceTask
from .train_task import OTESegmentationTrainingTask
from .nncf_task import OTESegmentationNNCFTask

from .ote_utils import get_task_class, load_template

__all__ = [
    'patch_config',
    'set_hyperparams',
    'get_task_class',
    'load_template',
    'OTESegmentationConfig',
    'OTESegmentationInferenceTask',
    'OTESegmentationTrainingTask',
    'OTESegmentationNNCFTask',
    'OpenVINOSegmentationTask',
]
