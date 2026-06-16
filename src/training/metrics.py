"""Метрики качества извлечения полей для модели Donut.
"""
from __future__ import annotations

import re

import zss


def parse_amount_loose(raw):
    if raw is None:
        return None
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


def get_total(parse):
    total = parse.get("total")
    if isinstance(total, dict):
        return total.get("total_price")
    return None


def total_accuracy(predictions, references):
    n = len(references)
    strict_hits = 0
    norm_hits = 0

    for pred, ref in zip(predictions, references):
        pred_total = get_total(pred) if isinstance(pred, dict) else None
        ref_total = get_total(ref)
        if pred_total is not None and ref_total is not None:
            if str(pred_total).strip() == str(ref_total).strip():
                strict_hits += 1
            if parse_amount_loose(pred_total) == parse_amount_loose(ref_total):
                norm_hits += 1

    return {
        "strict": strict_hits / n if n else 0.0,
        "normalized": norm_hits / n if n else 0.0,
    }


class _Node:
    def __init__(self, label, children=None):
        self.label = label
        self.children = children or []


def _dict_to_tree(obj, label="root"):
    node = _Node(label)
    if isinstance(obj, dict):
        for key in sorted(obj.keys()):
            node.children.append(_dict_to_tree(obj[key], key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            node.children.append(_dict_to_tree(item, f"[{i}]"))
    else:
        node.children.append(_Node(str(obj)))
    return node


def _get_children(node):
    return node.children


def _get_label(node):
    return node.label


def tree_edit_distance(pred, ref):
    pred_tree = _dict_to_tree(pred if isinstance(pred, dict) else {})
    ref_tree = _dict_to_tree(ref)
    dist = zss.simple_distance(pred_tree, ref_tree, _get_children, _get_label)
    ref_size = _tree_size(ref_tree)
    return dist / ref_size if ref_size else 0.0


def _tree_size(node):
    return 1 + sum(_tree_size(c) for c in node.children)


def mean_ted(predictions, references):
    if not references:
        return 0.0
    total = sum(tree_edit_distance(p, r) for p, r in zip(predictions, references))
    return total / len(references)