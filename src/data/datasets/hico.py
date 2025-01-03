# ------------------------------------------------------------------------
# HOTR official code : src/data/datasets/hico.py
# Copyright (c) Kakao Brain, Inc. and its affiliates. All Rights Reserved
# ------------------------------------------------------------------------
# Modified from QPIC (https://github.com/hitachi-rd-cv/qpic)
# Copyright (c) Hitachi, Ltd. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 [see LICENSE for details]
# ------------------------------------------------------------------------
from pathlib import Path
from PIL import Image
import json
from collections import defaultdict
import numpy as np

import torch
import torch.utils.data
import torchvision

# STIP is running as the main module.
# from src.data.datasets import builtin_meta
# import src.data.transforms.transforms as T

# STIP is running as a submodule.
from STIP.src.data.datasets import builtin_meta
import STIP.src.data.transforms.transforms as T

class HICODetection(torch.utils.data.Dataset):
    def __init__(self, img_set, img_folder, anno_file, action_list_file, transforms, num_queries):
        self.img_set = img_set
        self.img_folder = img_folder
        with open(anno_file, 'r') as f:
            self.annotations = json.load(f)
        with open(action_list_file, 'r') as f:
            self.action_lines = f.readlines()
        self._transforms = transforms
        self.num_queries = num_queries
        self.get_metadata()

        if img_set == 'train':
            self.ids = []
            for idx, img_anno in enumerate(self.annotations):
                for hoi in img_anno['hoi_annotation']:
                    if hoi['subject_id'] >= len(img_anno['annotations']) or hoi['object_id'] >= len(img_anno['annotations']):
                        break
                else:
                    self.ids.append(idx)
        else:
            self.ids = list(range(len(self.annotations)))
        # self.ids = self.ids[:1000]

    ############################################################################
    # Number Method
    ############################################################################
    def get_metadata(self):
        meta = builtin_meta._get_coco_instances_meta()
        self.COCO_CLASSES = meta['coco_classes']
        self._valid_obj_ids = [id for id in meta['thing_dataset_id_to_contiguous_id'].keys()]
        self._valid_verb_ids, self._valid_verb_names = [], []
        for action_line in self.action_lines[2:]:
            act_id, act_name = action_line.split()
            self._valid_verb_ids.append(int(act_id))
            self._valid_verb_names.append(act_name)

    def get_valid_obj_ids(self):
        return self._valid_obj_ids

    def get_actions(self):
        return self._valid_verb_names

    def num_category(self):
        return len(self.COCO_CLASSES)

    def num_action(self):
        return len(self._valid_verb_ids)
    ############################################################################

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, idx):
        img_anno = self.annotations[self.ids[idx]]

        img = Image.open(self.img_folder / img_anno['file_name']).convert('RGB')
        w, h = img.size

        if self.img_set == 'train':
            img_anno = merge_box_annotations(img_anno)
        # img_anno = merge_box_annotations(img_anno) # for finetune detr

        # cut out the GTs that exceed the number of object queries
        if self.img_set == 'train' and len(img_anno['annotations']) > self.num_queries:
            img_anno['annotations'] = img_anno['annotations'][:self.num_queries]

        boxes = [obj['bbox'] for obj in img_anno['annotations']]
        # guard against no boxes via resizing
        boxes = torch.as_tensor(boxes, dtype=torch.float32).reshape(-1, 4)

        # 由于STIP所用到的DETR目标检测器是91类，而不是80类。所以这里应该直接用category_id，而不是self._valid_obj_ids.index(obj['category_id'])
        if self.img_set == 'train':
            # Add index for confirming which boxes are kept after image transformation
            classes = [(i, obj['category_id']) for i, obj in enumerate(img_anno['annotations'])]
        else:
            classes = [obj['category_id'] for obj in img_anno['annotations']]
        classes = torch.tensor(classes, dtype=torch.int64)

        target = {}
        target['orig_size'] = torch.as_tensor([int(h), int(w)])
        target['size'] = torch.as_tensor([int(h), int(w)])
        if self.img_set == 'train':
            boxes[:, 0::2].clamp_(min=0, max=w)
            boxes[:, 1::2].clamp_(min=0, max=h)
            keep = (boxes[:, 3] > boxes[:, 1]) & (boxes[:, 2] > boxes[:, 0])
            boxes = boxes[keep]
            classes = classes[keep]

            target['boxes'] = boxes
            target['labels'] = classes
            target['iscrowd'] = torch.tensor([0 for _ in range(boxes.shape[0])])
            target['area'] = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

            if self._transforms is not None:
                img, target = self._transforms(img, target)

            kept_box_indices = [label[0] for label in target['labels']]

            target['labels'] = target['labels'][:, 1]

            obj_labels, verb_labels, sub_boxes, obj_boxes = [], [], [], []
            sub_obj_pairs = []
            for hoi in img_anno['hoi_annotation']:
                if hoi['subject_id'] not in kept_box_indices or hoi['object_id'] not in kept_box_indices:
                    continue
                sub_obj_pair = (hoi['subject_id'], hoi['object_id'])
                if sub_obj_pair in sub_obj_pairs: # multi label
                    verb_labels[sub_obj_pairs.index(sub_obj_pair)][self._valid_verb_ids.index(hoi['category_id'])] = 1
                else:
                    sub_obj_pairs.append(sub_obj_pair)
                    obj_labels.append(target['labels'][kept_box_indices.index(hoi['object_id'])])
                    verb_label = [0 for _ in range(len(self._valid_verb_ids))]
                    verb_label[self._valid_verb_ids.index(hoi['category_id'])] = 1
                    sub_box = target['boxes'][kept_box_indices.index(hoi['subject_id'])]
                    obj_box = target['boxes'][kept_box_indices.index(hoi['object_id'])]
                    verb_labels.append(verb_label)
                    sub_boxes.append(sub_box)
                    obj_boxes.append(obj_box)
            if len(sub_obj_pairs) == 0:
                target['pair_targets'] = torch.zeros((0,), dtype=torch.int64)
                target['pair_actions'] = torch.zeros((0, len(self._valid_verb_ids)), dtype=torch.float32)
                target['sub_boxes'] = torch.zeros((0, 4), dtype=torch.float32)
                target['obj_boxes'] = torch.zeros((0, 4), dtype=torch.float32)
            else:
                target['pair_targets'] = torch.stack(obj_labels)
                target['pair_actions'] = torch.as_tensor(verb_labels, dtype=torch.float32)
                target['sub_boxes'] = torch.stack(sub_boxes)
                target['obj_boxes'] = torch.stack(obj_boxes)

            # relation map
            relation_map = torch.zeros((len(target['boxes']), len(target['boxes']), self.num_action()))
            for sub_obj_pair in sub_obj_pairs:
                kept_subj_id = kept_box_indices.index(sub_obj_pair[0])
                kept_obj_id = kept_box_indices.index(sub_obj_pair[1])
                relation_map[kept_subj_id, kept_obj_id] = torch.tensor(verb_labels[sub_obj_pairs.index(sub_obj_pair)])
            target['relation_map'] = relation_map
            target['hois'] = relation_map.nonzero(as_tuple=False)
        else:
            target['boxes'] = boxes
            target['labels'] = classes
            target['id'] = idx

            if self._transforms is not None:
                img, _ = self._transforms(img, None)

            hois = []
            for hoi in img_anno['hoi_annotation']:
                hois.append((hoi['subject_id'], hoi['object_id'], self._valid_verb_ids.index(hoi['category_id'])))
            target['hois'] = torch.as_tensor(hois, dtype=torch.int64)

        target['image_id'] = torch.tensor([idx])
        return img, target

    def set_rare_hois(self, anno_file):
        with open(anno_file, 'r') as f:
            annotations = json.load(f)

        counts = defaultdict(lambda: 0)
        for img_anno in annotations:
            hois = img_anno['hoi_annotation']
            bboxes = img_anno['annotations']
            for hoi in hois:
                # mapped to valid obj ids for evaludation
                triplet = (self._valid_obj_ids.index(bboxes[hoi['subject_id']]['category_id']),
                           self._valid_obj_ids.index(bboxes[hoi['object_id']]['category_id']),
                           self._valid_verb_ids.index(hoi['category_id']))
                counts[triplet] += 1
        self.rare_triplets = []
        self.non_rare_triplets = []
        for triplet, count in counts.items():
            if count < 10:
                self.rare_triplets.append(triplet)
            else:
                self.non_rare_triplets.append(triplet)

    def load_correct_mat(self, path):
        self.correct_mat = np.load(path)


# Add color jitter to coco transforms
def make_hico_transforms(image_set):

    normalize = T.Compose([
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    scales = [480, 512, 544, 576, 608, 640, 672, 704, 736, 768, 800]

    if image_set == 'train':
        return T.Compose([
            T.RandomHorizontalFlip(),
            T.ColorJitter(.4, .4, .4),
            T.RandomSelect(
                T.RandomResize(scales, max_size=1333),
                T.Compose([
                    T.RandomResize([400, 500, 600]),
                    T.RandomSizeCrop(384, 600),
                    T.RandomResize(scales, max_size=1333),
                ])
            ),
            normalize,
        ])

    if image_set == 'val':
        return T.Compose([
            T.RandomResize([800], max_size=1333),
            normalize,
        ])

    if image_set == 'test':
        return T.Compose([
            T.RandomResize([800], max_size=1333),
            normalize,
        ])

    raise ValueError(f'unknown {image_set}')


def merge_box_annotations(org_image_annotation, overlap_iou_thres=0.7):
    merged_image_annotation = org_image_annotation.copy()

    # compute match
    bbox_list = org_image_annotation['annotations']
    box_match = torch.zeros(len(bbox_list), len(bbox_list)).bool()
    for i, bbox1 in enumerate(bbox_list):
        for j, bbox2 in enumerate(bbox_list):
            box_match[i, j] = compute_box_match(bbox1, bbox2, overlap_iou_thres)

    box_groups = []
    for i in range(len(box_match)):
        if box_match[i].any():  # box unassigned to group
            group_ids = box_match[i].nonzero(as_tuple=False).squeeze(1)
            box_groups.append(group_ids.tolist())
            box_match[:, group_ids] = False
    assert sum([len(g) for g in box_groups]) == len(bbox_list)

    # merge to new anntations
    group_info, orgbox2group = [], {}
    for gid, org_box_ids in enumerate(box_groups):
        for orgid in org_box_ids: orgbox2group.update({orgid: gid})
        # selected_box_id = np.random.choice(org_box_ids)
        # box_info = bbox_list[selected_box_id]
        box_info = {
            'bbox': torch.tensor([bbox_list[id]['bbox'] for id in org_box_ids]).float().mean(dim=0).int().tolist(),
            'category_id': bbox_list[org_box_ids[0]]['category_id']
        }

        group_info.append(box_info)

    new_hois = []
    for hoi in org_image_annotation['hoi_annotation']:
        if hoi['subject_id'] in orgbox2group and hoi['object_id'] in orgbox2group:
            new_hois.append({
                'subject_id': orgbox2group[hoi['subject_id']],
                'object_id': orgbox2group[hoi['object_id']],
                'category_id': hoi['category_id']
            })

    merged_image_annotation['annotations'] = group_info
    merged_image_annotation['hoi_annotation'] = new_hois
    return merged_image_annotation

# iou > threshold and same category
def compute_box_match(bbox1, bbox2, threshold):
    if isinstance(bbox1['category_id'], str):
        bbox1['category_id'] = int(bbox1['category_id'].replace('\n', ''))
    if isinstance(bbox2['category_id'], str):
        bbox2['category_id'] = int(bbox2['category_id'].replace('\n', ''))
    if bbox1['category_id'] != bbox2['category_id']:
        return False
    else:
        rec1 = bbox1['bbox']
        rec2 = bbox2['bbox']
        # computing area of each rectangles
        S_rec1 = (rec1[2] - rec1[0]+1) * (rec1[3] - rec1[1]+1)
        S_rec2 = (rec2[2] - rec2[0]+1) * (rec2[3] - rec2[1]+1)

        # computing the sum_area
        sum_area = S_rec1 + S_rec2

        # find the each edge of intersect rectangle
        left_line = max(rec1[1], rec2[1])
        right_line = min(rec1[3], rec2[3])
        top_line = max(rec1[0], rec2[0])
        bottom_line = min(rec1[2], rec2[2])

        # judge if there is an intersect
        intersect = max((right_line - left_line+1), 0) * max((bottom_line - top_line+1), 0)
        iou = intersect / (sum_area - intersect)
        if iou > threshold:
            return True
        else:
            return False

def build(image_set, args):
    root = Path(args.data_path)
    assert root.exists(), f'provided HOI path {root} does not exist'
    PATHS = {
        'train': (root / 'images' / 'train2015', root / 'annotations' / 'shuffled_trainval_hico_first300.json'),
        'val': (root / 'images' / 'test2015', root / 'annotations' / 'shuffled_test_hico_first300.json'),
        'test': (root / 'images' / 'test2015', root / 'annotations' / 'shuffled_test_hico_first300.json')
    }
    # PATHS = {
    #     'train': (root / 'images' / 'train2015', root / 'annotations' / 'trainval_hico.json'),
    #     'val': (root / 'images' / 'test2015', root / 'annotations' / 'test_hico.json'),
    #     'test': (root / 'images' / 'test2015', root / 'annotations' / 'test_hico.json')
    # }
    CORRECT_MAT_PATH = root / 'annotations' / 'corre_hico_shuffled_first300.npy'
    # CORRECT_MAT_PATH = root / 'annotations' / 'corre_hico.npy'
    action_list_file = root / 'list_action.txt'

    img_folder, anno_file = PATHS[image_set]
    dataset = HICODetection(image_set, img_folder, anno_file, action_list_file, transforms=make_hico_transforms(image_set),
                            num_queries=args.num_queries)
    if image_set == 'val' or image_set == 'test':
        dataset.set_rare_hois(PATHS['train'][1])
        dataset.load_correct_mat(CORRECT_MAT_PATH)
    return dataset