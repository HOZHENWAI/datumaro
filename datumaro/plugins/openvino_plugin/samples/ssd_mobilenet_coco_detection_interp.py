# Copyright (C) 2021 Intel Corporation
#
# SPDX-License-Identifier: MIT


from datumaro.components.extractor import *

conf_thresh = 0.3
model_class_num = 91


def _match_confs(confs, detections):
    matches = [-1] * len(detections)

    queries = {}
    for i, det in enumerate(detections):
        queries.setdefault(int(det[1]), []).append((det[2], i))

    found_count = 0
    for i, v in enumerate(confs):
        if found_count == len(detections):
            break

        for cls_id, query in queries.items():
            if found_count == len(detections):
                break

            for q_id, (conf, det_idx) in enumerate(query):
                if v[cls_id] == conf:
                    matches[det_idx] = i
                    query.pop(q_id)
                    found_count += 1
                    break

    return matches


def process_outputs(inputs, outputs):
    # inputs = model input; array or images; shape = (B, H, W, C)
    # outputs = model output; shape = (1, 1, N, 7); N is the number of detected bounding boxes.
    # det = [image_id, label(class id), conf, x_min, y_min, x_max, y_max]
    # results = conversion result; [[ Annotation, ... ], ... ]

    results = []
    for input, confs, detections in zip(
        inputs, outputs["do_ExpandDims_conf/sigmoid"], outputs["DetectionOutput"]
    ):

        input_height, input_width = input.shape[:2]

        confs = confs[0].reshape(-1, model_class_num)
        detections = detections[0]

        conf_ids = _match_confs(confs, detections)

        image_results = []
        for i, det in enumerate(detections):
            image_id = int(det[0])
            label = int(det[1])
            conf = float(det[2])
            det_confs = confs[conf_ids[i]]

            if conf <= conf_thresh:
                continue

            x = max(int(det[3] * input_width), 0)
            y = max(int(det[4] * input_height), 0)
            w = min(int(det[5] * input_width - x), input_width)
            h = min(int(det[6] * input_height - y), input_height)

            image_results.append(Bbox(x, y, w, h, label=label, 
                attributes={ 'score': conf, 'scores': list(map(float, det_confs)) }
            ))
            
            results.append(image_results)

    return results


def get_categories():
    # output categories - label map etc.

    label_categories = LabelCategories()

    with open("samples/coco.class", "r") as file:
        for line in file.readlines():
            label = line.strip()
            label_categories.add(label)

    return {AnnotationType.label: label_categories}