# pre-trained params settings
ignore_keys = [r'^backbone\.increase_modules\.', r'^backbone\.downsample_modules\.',
               r'^backbone\.final_layer\.', r'^backbone\.aggregator\.',
               r'^backbone\.out_modules\.', r'^head\.', r'^decode_head\.',
               r'^auxiliary_head\.']

# model settings
norm_cfg = dict(type='SyncBN', requires_grad=True)
model = dict(
    type='EncoderDecoder',
    pretrained=None,
    backbone=dict(
        type='LiteHRNet',
        norm_cfg=norm_cfg,
        norm_eval=False,
        extra=dict(
            stem=dict(
                stem_channels=32,
                out_channels=32,
                expand_ratio=1,
                strides=(2, 1),
                extra_stride=False,
                input_norm=False,
                out_pool=True,
            ),
            num_stages=3,
            stages_spec=dict(
                weighting_module_version='v1',
                num_modules=(3, 8, 3),
                num_branches=(2, 3, 4),
                num_blocks=(2, 2, 2),
                module_type=('LITE', 'LITE', 'LITE'),
                with_fuse=(True, True, True),
                reduce_ratios=(8, 8, 8),
                num_channels=(
                    (40, 80),
                    (40, 80, 160),
                    (40, 80, 160, 320),
                )
            ),
            out_modules=dict(
                conv=dict(
                    enable=False,
                    channels=280
                ),
                position_att=dict(
                    enable=False,
                    key_channels=128,
                    value_channels=280,
                    psp_size=(1, 3, 6, 8),
                ),
                local_att=dict(
                    enable=False
                )
            ),
            out_aggregator=dict(
                enable=True
            ),
            add_stem_features=True,
            add_input=False
        )
    ),
    decode_head=dict(
        type='FCNHead',
        in_channels=40,
        in_index=0,
        channels=40,
        input_transform=None,
        kernel_size=1,
        num_convs=0,
        concat_input=False,
        dropout_ratio=-1,
        num_classes=19,
        norm_cfg=norm_cfg,
        align_corners=False,
        loss_decode=dict(
            type='CrossEntropyLoss',
            use_sigmoid=False,
            sampler=dict(type='MaxPoolingPixelSampler', ratio=0.25, p=1.7),
            loss_weight=1.0
        )
    ),
    # model training and testing settings
    train_cfg=dict(),
    test_cfg=dict(mode='whole')
)
