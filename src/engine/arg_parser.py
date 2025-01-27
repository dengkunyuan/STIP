# ------------------------------------------------------------------------
# HOTR official code : engine/arg_parser.py
# Copyright (c) Kakao Brain, Inc. and its affiliates. All Rights Reserved
# Modified arguments are represented with *
# ------------------------------------------------------------------------
# Modified from DETR (https://github.com/facebookresearch/detr)
# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
# ------------------------------------------------------------------------
import argparse
# ACIL: 避免特定于ACIL的命令行参数影响STIP的参数解析，因此直接给出STIP的参数
from argparse import Namespace

def get_args_parser():
    parser = argparse.ArgumentParser('Set transformer detector', add_help=False)
    parser.add_argument('--lr', default=1e-4, type=float)
    parser.add_argument('--lr_backbone', default=1e-5, type=float)
    parser.add_argument('--batch_size', default=2, type=int)
    parser.add_argument('--weight_decay', default=1e-4, type=float)
    parser.add_argument('--epochs', default=100, type=int)
    parser.add_argument('--lr_drop', default=80, type=int)
    parser.add_argument('--clip_max_norm', default=0.1, type=float,
                        help='gradient clipping max norm')

    # DETR Model parameters
    parser.add_argument('--frozen_weights', type=str, default=None,
                        help="Path to the pretrained model. If set, only the mask head will be trained")
    # DETR Backbone
    parser.add_argument('--backbone', default='resnet50', type=str,
                        help="Name of the convolutional backbone to use")
    parser.add_argument('--dilation', action='store_true',
                        help="If true, we replace stride with dilation in the last convolutional block (DC5)")
    parser.add_argument('--position_embedding', default='sine', type=str, choices=('sine', 'learned'),
                        help="Type of positional embedding to use on top of the image features")

    # DETR Transformer (= Encoder, Instance Decoder)
    parser.add_argument('--enc_layers', default=6, type=int,
                        help="Number of encoding layers in the transformer")
    parser.add_argument('--dec_layers', default=6, type=int,
                        help="Number of decoding layers in the transformer")
    parser.add_argument('--dim_feedforward', default=2048, type=int,
                        help="Intermediate size of the feedforward layers in the transformer blocks")
    parser.add_argument('--hidden_dim', default=256, type=int,
                        help="Size of the embeddings (dimension of the transformer)")
    parser.add_argument('--dropout', default=0.1, type=float,
                        help="Dropout applied in the transformer")
    parser.add_argument('--nheads', default=8, type=int,
                        help="Number of attention heads inside the transformer's attentions")
    parser.add_argument('--num_queries', default=100, type=int,
                        help="Number of query slots")
    parser.add_argument('--pre_norm', action='store_true')

    # Segmentation
    parser.add_argument('--masks', action='store_true',
                        help="Train segmentation head if the flag is provided")

    # Loss Option
    parser.add_argument('--no_aux_loss', dest='aux_loss', action='store_false',
                        help="Disables auxiliary decoding losses (loss at each layer)")

    # Loss coefficients (DETR)
    parser.add_argument('--mask_loss_coef', default=1, type=float)
    parser.add_argument('--dice_loss_coef', default=1, type=float)
    parser.add_argument('--bbox_loss_coef', default=5, type=float)
    parser.add_argument('--giou_loss_coef', default=2, type=float)
    parser.add_argument('--eos_coef', default=0.1, type=float,
                        help="Relative classification weight of the no-object class")

    # Matcher (DETR)
    parser.add_argument('--set_cost_class', default=1, type=float,
                        help="Class coefficient in the matching cost")
    parser.add_argument('--set_cost_bbox', default=5, type=float,
                        help="L1 box coefficient in the matching cost")
    parser.add_argument('--set_cost_giou', default=2, type=float,
                        help="giou box coefficient in the matching cost")

    # * HOI Detection
    parser.add_argument('--HOIDet', action='store_true',
                        help="Train HOI Detection head if the flag is provided")
    parser.add_argument('--share_enc', action='store_true',
                        help="Share the Encoder in DETR for HOI Detection if the flag is provided")
    parser.add_argument('--pretrained_dec', action='store_true',
                        help="Use Pre-trained Decoder in DETR for Interaction Decoder if the flag is provided")                        
    parser.add_argument('--hoi_enc_layers', default=1, type=int,
                        help="Number of decoding layers in HOI transformer")
    parser.add_argument('--hoi_dec_layers', default=6, type=int,
                        help="Number of decoding layers in HOI transformer")
    parser.add_argument('--hoi_nheads', default=8, type=int,
                        help="Number of decoding layers in HOI transformer")
    parser.add_argument('--hoi_dim_feedforward', default=2048, type=int,
                        help="Number of decoding layers in HOI transformer")
    # parser.add_argument('--hoi_mode', type=str, default=None, help='[inst | pair | all]')
    parser.add_argument('--num_hoi_queries', default=32, type=int,
                        help="Number of Queries for Interaction Decoder")
    parser.add_argument('--hoi_aux_loss', action='store_true')


    # * HOTR Matcher
    parser.add_argument('--set_cost_idx', default=1, type=float,
                        help="IDX coefficient in the matching cost")
    parser.add_argument('--set_cost_act', default=1, type=float,
                        help="Action coefficient in the matching cost")
    parser.add_argument('--set_cost_tgt', default=1, type=float,
                        help="Target coefficient in the matching cost")

    # * HOTR Loss coefficients
    parser.add_argument('--temperature', default=0.05, type=float, help="temperature")
    parser.add_argument('--hoi_idx_loss_coef', default=1, type=float)
    parser.add_argument('--hoi_act_loss_coef', default=1, type=float)
    parser.add_argument('--hoi_tgt_loss_coef', default=1, type=float)
    parser.add_argument('--hoi_eos_coef', default=0.1, type=float, help="Relative classification weight of the no-object class")

    # * dataset parameters
    parser.add_argument('--dataset_file', help='[coco | vcoco]')
    parser.add_argument('--data_path', type=str)
    parser.add_argument('--object_threshold', type=float, default=0, help='Threshold for object confidence')

    # machine parameters
    parser.add_argument('--output_dir', default='',
                        help='path where to save, empty for no saving')
    parser.add_argument('--custom_path', default='',
                        help="Data path for custom inference. Only required for custom_main.py")
    parser.add_argument('--device', default='cuda',
                        help='device to use for training / testing')
    parser.add_argument('--seed', default=42, type=int)
    parser.add_argument('--resume', default='', help='resume from checkpoint')
    parser.add_argument('--start_epoch', default=0, type=int, metavar='N',
                        help='start epoch')
    parser.add_argument('--num_workers', default=4, type=int)

    # mode
    parser.add_argument('--eval', action='store_true', help="Only evaluate results if the flag is provided")
    parser.add_argument('--validate', action='store_true', help="Validate after every epoch")

    # distributed training parameters
    parser.add_argument('--world_size', default=1, type=int,
                        help='number of distributed processes')
    parser.add_argument('--dist_url', default='env://', help='url used to set up distributed training')

    # * WanDB
    parser.add_argument('--wandb', action='store_true')
    parser.add_argument('--project_name', default='HOTR')
    parser.add_argument('--group_name', default='KakaoBrain')
    parser.add_argument('--run_name', default='run_000001')

    # STIP
    parser.add_argument('--STIP_relation_head', action='store_true', default=False)
    parser.add_argument('--finetune_detr', action='store_true', default=False)
    parser.add_argument('--use_high_resolution_relation_feature_map', action='store_true', default=False)


    # 把STIP_main.py中的参数加入到parser中，方便调用
    # training
    parser.add_argument('--detr_weights', default=None, type=str)
    parser.add_argument('--train_detr', action='store_true', default=False)
    parser.add_argument('--finetune_detr_weight', default=0.1, type=float)
    parser.add_argument('--lr_detr', default=1e-5, type=float)
    parser.add_argument('--reduce_lr_on_plateau_patience', default=2, type=int)
    parser.add_argument('--reduce_lr_on_plateau_factor', default=0.1, type=float)

    # loss
    parser.add_argument('--proposal_focal_loss_alpha', default=0.75, type=float) # large alpha for high recall
    parser.add_argument('--action_focal_loss_alpha', default=0.5, type=float)
    parser.add_argument('--proposal_focal_loss_gamma', default=2, type=float)
    parser.add_argument('--action_focal_loss_gamma', default=2, type=float)
    parser.add_argument('--proposal_loss_coef', default=1, type=float)
    parser.add_argument('--action_loss_coef', default=1, type=float)

    # ablations
    parser.add_argument('--no_hard_mining_for_relation_discovery', dest='use_hard_mining_for_relation_discovery', action='store_false', default=True)
    parser.add_argument('--no_relation_dependency_encoding', dest='use_relation_dependency_encoding', action='store_false', default=True)
    parser.add_argument('--no_memory_layout_encoding', dest='use_memory_layout_encoding', action='store_false', default=True, help='layout encodings')
    parser.add_argument('--no_nms_on_detr', dest='apply_nms_on_detr', action='store_false', default=True)
    parser.add_argument('--no_tail_semantic_feature', dest='use_tail_semantic_feature', action='store_false', default=True)
    parser.add_argument('--no_spatial_feature', dest='use_spatial_feature', action='store_false', default=True)
    parser.add_argument('--no_interaction_decoder', action='store_true', default=False)

    # not sensitive or effective
    parser.add_argument('--use_memory_union_mask', action='store_true', default=False)
    parser.add_argument('--use_union_feature', action='store_true', default=False)
    parser.add_argument('--adaptive_relation_query_num', action='store_true', default=False)
    parser.add_argument('--use_relation_tgt_mask', action='store_true', default=False)
    parser.add_argument('--use_relation_tgt_mask_attend_topk', default=10, type=int)
    parser.add_argument('--use_prior_verb_label_mask', action='store_true', default=False)
    parser.add_argument('--relation_feature_map_from', default='backbone', help='backbone | detr_encoder')
    parser.add_argument('--use_query_fourier_encoding', action='store_true', default=False)

    return parser


# ACIL: 避免特定于ACIL的命令行参数影响STIP的参数解析，因此直接给出STIP的参数
def get_args():
    args_dict = {
        'lr': 1e-4,
        'lr_backbone': 1e-5,
        'batch_size': 2,
        'weight_decay': 1e-4,
        'epochs': 100,
        'lr_drop': 80,
        'clip_max_norm': 0.1,
        'frozen_weights': None,
        'backbone': 'resnet50',
        'dilation': False,
        'position_embedding': 'sine',
        'enc_layers': 6,
        'dec_layers': 6,
        'dim_feedforward': 2048,
        'hidden_dim': 256,
        'dropout': 0.1,
        'nheads': 8,
        'num_queries': 100,
        'pre_norm': False,
        'masks': False,
        'no_aux_loss': True,
        'aux_loss': True,
        'mask_loss_coef': 1,
        'dice_loss_coef': 1,
        'bbox_loss_coef': 5,
        'giou_loss_coef': 2,
        'eos_coef': 0.1,
        'set_cost_class': 1,
        'set_cost_bbox': 5,
        'set_cost_giou': 2,
        'HOIDet': False,
        'share_enc': False,
        'pretrained_dec': False,
        'hoi_enc_layers': 1,
        'hoi_dec_layers': 6,
        'hoi_nheads': 8,
        'hoi_dim_feedforward': 2048,
        'num_hoi_queries': 32,
        'hoi_aux_loss': False,
        'set_cost_idx': 1,
        'set_cost_act': 1,
        'set_cost_tgt': 1,
        'temperature': 0.05,
        'hoi_idx_loss_coef': 1,
        'hoi_act_loss_coef': 1,
        'hoi_tgt_loss_coef': 1,
        'hoi_eos_coef': 0.1,
        'dataset_file': None,
        'data_path': None,
        'object_threshold': 0,
        'output_dir': '',
        'custom_path': '',
        'device': 'cuda',
        'seed': 42,
        'resume': '',
        'start_epoch': 0,
        'num_workers': 4,
        'eval': False,
        'validate': False,
        'world_size': 1,
        'dist_url': 'env://',
        'wandb': False,
        'project_name': 'HOTR',
        'group_name': 'KakaoBrain',
        'run_name': 'run_000001',
        'STIP_relation_head': False,
        'finetune_detr': False,
        'use_high_resolution_relation_feature_map': False,
        'detr_weights': None,
        'train_detr': False,
        'finetune_detr_weight': 0.1,
        'lr_detr': 1e-5,
        'reduce_lr_on_plateau_patience': 2,
        'reduce_lr_on_plateau_factor': 0.1,
        'proposal_focal_loss_alpha': 0.75,
        'action_focal_loss_alpha': 0.5,
        'proposal_focal_loss_gamma': 2,
        'action_focal_loss_gamma': 2,
        'proposal_loss_coef': 1,
        'action_loss_coef': 1,
        'no_hard_mining_for_relation_discovery': True,
        'use_hard_mining_for_relation_discovery': True,
        'no_relation_dependency_encoding': True,
        'use_relation_dependency_encoding': True,
        'no_memory_layout_encoding': True,
        'use_memory_layout_encoding': True,
        'no_nms_on_detr': True,
        'apply_nms_on_detr': True,
        'no_tail_semantic_feature': True,
        'use_tail_semantic_feature': True,
        'no_spatial_feature': True,
        'use_spatial_feature': True,
        'no_interaction_decoder': False,
        'use_memory_union_mask': False,
        'use_union_feature': False,
        'adaptive_relation_query_num': False,
        'use_relation_tgt_mask': False,
        'use_relation_tgt_mask_attend_topk': 10,
        'use_prior_verb_label_mask': False,
        'relation_feature_map_from': 'backbone',
        'use_query_fourier_encoding': False
    }
    # 转换为Namespace类型
    args = Namespace(**args_dict)

    return args