# Copyright (c) 2020-2021 The MMSegmentation Authors
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

import torch
import torch.nn as nn
import torch.nn.functional as F
from mmcv.cnn import ConvModule, DepthwiseSeparableConvModule

from mmseg.ops import resize
from ..builder import HEADS
from ..utils import SelfAttentionBlock as _SelfAttentionBlock
from .cascade_decode_head import BaseCascadeDecodeHead


class SpatialGatherModule(nn.Module):
    """Aggregate the context features according to the initial predicted
    probability distribution.

    Employ the soft-weighted method to aggregate the context.
    """

    def __init__(self, scale=1.0):
        super(SpatialGatherModule, self).__init__()

        self.scale = scale
        assert self.scale > 0.0

    def forward(self, feats, prev_logits):
        """Forward function."""

        batch_size, num_classes, height, width = prev_logits.size()
        channels = feats.size(1)

        prev_logits = prev_logits.view(batch_size, num_classes, -1)
        feats = feats.view(batch_size, channels, -1)

        feats = feats.permute(0, 2, 1)  # [batch_size, height*width, channels]
        probs = F.softmax(self.scale * prev_logits, dim=2)  # [batch_size, num_classes, height*width]

        out_context = torch.matmul(probs, feats)  # [batch_size, num_classes, channels]
        out_context = out_context.permute(0, 2, 1).contiguous().unsqueeze(3)  # [batch_size, channels, num_classes, 1]

        return out_context


class ObjectAttentionBlock(_SelfAttentionBlock):
    """Make a OCR used SelfAttentionBlock."""

    def __init__(self, in_channels, channels, scale, conv_cfg, norm_cfg, act_cfg, out_act_cfg):
        if scale > 1:
            query_downsample = nn.MaxPool2d(kernel_size=scale)
        else:
            query_downsample = None

        super(ObjectAttentionBlock, self).__init__(
            key_in_channels=in_channels,
            query_in_channels=in_channels,
            channels=channels,
            out_channels=in_channels,
            share_key_query=False,
            query_downsample=query_downsample,
            key_downsample=None,
            key_query_num_convs=2,
            key_query_norm=True,
            value_out_num_convs=1,
            value_out_norm=True,
            matmul_norm=True,
            with_out=True,
            conv_cfg=conv_cfg,
            norm_cfg=norm_cfg,
            act_cfg=act_cfg,
        )

        self.bottleneck = ConvModule(
            2 * in_channels,
            in_channels,
            kernel_size=1,
            conv_cfg=conv_cfg,
            norm_cfg=norm_cfg,
            act_cfg=act_cfg if out_act_cfg == 'default' else out_act_cfg,
        )

    def forward(self, query_feats, key_feats):
        """Forward function."""

        context = super(ObjectAttentionBlock, self).forward(query_feats, key_feats)

        output = self.bottleneck(torch.cat([context, query_feats], dim=1))
        if self.query_downsample is not None:
            output = resize(query_feats)

        return output


@HEADS.register_module()
class OCRHead(BaseCascadeDecodeHead):
    """Object-Contextual Representations for Semantic Segmentation.

    This head is the implementation of `OCRNet
    <https://arxiv.org/abs/1909.11065>`_.

    Args:
        ocr_channels (int): The intermediate channels of OCR block.
        scale (int): The scale of probability map in SpatialGatherModule in
            Default: 1.
    """

    def __init__(self, ocr_channels, scale=1, spatial_scale=1.0, out_act_cfg='default', sep_conv=False, **kwargs):
        super(OCRHead, self).__init__(**kwargs)

        self.ocr_channels = ocr_channels
        self.scale = scale
        self.spatial_scale = spatial_scale

        self.bottleneck = self._build_conv_module(
            sep_conv,
            self.in_channels,
            self.channels,
            kernel_size=3,
            padding=1,
            conv_cfg=self.conv_cfg,
            norm_cfg=self.norm_cfg,
            act_cfg=self.act_cfg
        )
        self.object_context_block = ObjectAttentionBlock(
            self.channels,
            self.ocr_channels,
            scale=self.scale,
            conv_cfg=self.conv_cfg,
            norm_cfg=self.norm_cfg,
            act_cfg=self.act_cfg,
            out_act_cfg=out_act_cfg
        )
        self.spatial_gather_module = SpatialGatherModule(
            scale=self.spatial_scale
        )

    @staticmethod
    def _build_conv_module(sep_conv, in_channels, out_channels, **kwargs):
        if sep_conv:
            return DepthwiseSeparableConvModule(
                in_channels,
                out_channels,
                dw_act_cfg=None,
                **kwargs
            )
        else:
            return ConvModule(
                in_channels,
                out_channels,
                **kwargs
            )

    def forward(self, inputs, prev_output):
        """Forward function."""

        x = self._transform_inputs(inputs)

        feats = self.bottleneck(x)
        context = self.spatial_gather_module(feats, prev_output)
        augmented_feat = self.object_context_block(feats, context)

        output = self.cls_seg(augmented_feat)

        return output
