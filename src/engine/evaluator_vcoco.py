# ------------------------------------------------------------------------
# HOTR official code : src/engine/evaluator_vcoco.py
# Copyright (c) Kakao Brain, Inc. and its affiliates. All Rights Reserved
# ------------------------------------------------------------------------
# Modified from DETR (https://github.com/facebookresearch/detr)
# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
# ------------------------------------------------------------------------
import os
import torch
import time
import datetime

# STIP is running as the main module.
# import src.util.misc as utils
# import src.util.logger as loggers
# from src.data.evaluators.vcoco_eval import VCocoEvaluator
# from src.util.box_ops import rescale_bboxes, rescale_pairs
# from src.models.stip_utils import check_annotation, plot_cross_attention

# STIP is running as a submodule.
import STIP.src.util.misc as utils
import STIP.src.util.logger as loggers
from STIP.src.data.evaluators.vcoco_eval import VCocoEvaluator
from STIP.src.util.box_ops import rescale_bboxes, rescale_pairs
from STIP.src.models.stip_utils import check_annotation, plot_cross_attention

import wandb

@torch.no_grad()
def vcoco_evaluate(model, criterion, postprocessors, data_loader, device, output_dir, thr):
    model.eval()
    criterion.eval()

    metric_logger = loggers.MetricLogger(mode="test", delimiter="  ")
    header = 'Evaluation Inference (V-COCO)'

    print_freq = 1 # len(data_loader)
    res = {}
    hoi_recognition_time = []

    for samples, targets in metric_logger.log_every(data_loader, print_freq, header):
        samples = samples.to(device)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        # dec_selfattn_weights, dec_crossattn_weights = [], []
        # hook = model.interaction_decoder.layers[-1].multihead_attn.register_forward_hook(lambda self, input, output: dec_crossattn_weights.append(output[1]))

        outputs = model(samples)
        loss_dict = criterion(outputs, targets)
        loss_dict_reduced = utils.reduce_dict(loss_dict) # ddp gathering

        loss_dict_reduced_scaled = {k: v * criterion.weight_dict[k] for k, v in loss_dict_reduced.items() if k in criterion.weight_dict}
        loss_value = sum(loss_dict_reduced_scaled.values()).item()

        orig_target_sizes = torch.stack([t["orig_size"] for t in targets], dim=0)
        results = postprocessors['hoi'](outputs, orig_target_sizes, threshold=thr, dataset='vcoco')
        targets = process_target(targets, orig_target_sizes)
        hoi_recognition_time.append(results[0]['hoi_recognition_time'] * 1000)

        # check_annotation(samples, targets, mode='eval', rel_num=20, dataset='vcoco')
        # plot_cross_attention(samples, outputs, targets, dec_crossattn_weights, dataset='vcoco'); hook.remove()

        res.update(
            {target['image_id'].item():\
                {'target': target, 'prediction': output} for target, output in zip(targets, results)
            }
        )
        metric_logger.update(loss=loss_value, **loss_dict_reduced_scaled)
        # if len(res) > 10: break

    print(f"[stats] HOI Recognition Time (avg) : {sum(hoi_recognition_time)/len(hoi_recognition_time):.4f} ms")
    metric_logger.synchronize_between_processes()
    print("Averaged validation stats:", metric_logger)

    start_time = time.time()
    gather_res = utils.all_gather(res)
    total_res = {}
    for dist_res in gather_res:
        total_res.update(dist_res)
    total_time = time.time() - start_time
    total_time_str = str(datetime.timedelta(seconds=int(total_time)))
    print(f"[stats] Distributed Gathering Time : {total_time_str}")

    return total_res

def vcoco_accumulate(total_res, args, print_results, wandb_log):
    vcoco_evaluator = VCocoEvaluator(args)
    vcoco_evaluator.update(total_res)    
    print(f"[stats] Score Matrix Generation completed!!          ")

    scenario1 = vcoco_evaluator.role_eval1.evaluate(print_results)
    scenario2 = vcoco_evaluator.role_eval2.evaluate(print_results)

    if wandb_log:
        wandb.log({
            'scenario1': scenario1,
            'scenario2': scenario2
        })

    return scenario1, scenario2

def process_target(targets, target_sizes):
    for idx, (target, target_size) in enumerate(zip(targets, target_sizes)):
        labels = target['labels']
        valid_boxes_inds = (labels > 0)

        targets[idx]['boxes'] = rescale_bboxes(target['boxes'], target_size) # boxes
        targets[idx]['pair_boxes'] = rescale_pairs(target['pair_boxes'], target_size) # pairs

    return targets