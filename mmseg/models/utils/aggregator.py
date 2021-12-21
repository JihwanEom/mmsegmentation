import torch.nn as nn
import torch.nn.functional as F
from mmcv.cnn import DepthwiseSeparableConvModule, ConvModule

from mmseg.core.ops.math import normalize


class IterativeAggregator(nn.Module):
    """The original repo: https://github.com/HRNet/Lite-HRNet"""

    def __init__(self, in_channels, min_channels=None, conv_cfg=None, norm_cfg=dict(type='BN'), merge_norm=None):
        super().__init__()

        num_branches = len(in_channels)
        self.in_channels = in_channels[::-1]

        min_channels = min_channels if min_channels is not None else 0
        assert min_channels >= 0

        projects, expanders = [], []
        for i in range(num_branches):
            if i != num_branches - 1:
                out_channels = self.in_channels[i + 1]
            else:
                out_channels = self.in_channels[i]

            projects.append(DepthwiseSeparableConvModule(
                in_channels=max(self.in_channels[i], min_channels),
                out_channels=max(out_channels, min_channels),
                kernel_size=3,
                stride=1,
                padding=1,
                conv_cfg=conv_cfg,
                norm_cfg=norm_cfg,
                act_cfg=dict(type='ReLU'),
                dw_act_cfg=None,
                pw_act_cfg=dict(type='ReLU')
            ))

            if self.in_channels[i] < min_channels:
                expanders.append(ConvModule(
                    in_channels=self.in_channels[i],
                    out_channels=min_channels,
                    kernel_size=1,
                    stride=1,
                    conv_cfg=conv_cfg,
                    norm_cfg=norm_cfg,
                    act_cfg=dict(type='ReLU')
                ))
            else:
                expanders.append(None)

        self.projects = nn.ModuleList(projects)
        self.expanders = nn.ModuleList(expanders)

        assert merge_norm in [None, 'none', 'channel', 'spatial']
        self.merge_norm = merge_norm
    
    @staticmethod
    def _norm(x, mode=None):
        if mode is None or mode == 'none':
            out = x
        elif mode == 'channel':
            out = normalize(x, dim=1, p=2)
        else:
            _, c, h, w = x.size()
            y = x.view(-1, c, h * w)
            y = normalize(y, dim=2, p=2)
            out = y.view(-1, c, h, w)
        
        return out

    def forward(self, x):
        x = x[::-1]

        y_list = []
        last_x = None
        for i, s in enumerate(x):
            if self.expanders[i] is not None:
                s = self.expanders[i](s)

            if last_x is not None:
                last_x = F.interpolate(
                    last_x,
                    size=s.size()[-2:],
                    mode='bilinear',
                    align_corners=True
                )

                norm_s = self._norm(s, self.merge_norm)
                norm_x = self._norm(last_x, self.merge_norm)
                
                s = norm_s + norm_x

            s = self.projects[i](s)
            last_x = s

            y_list.append(s)

        return y_list[::-1]
