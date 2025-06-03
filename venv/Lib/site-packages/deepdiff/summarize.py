from typing import Tuple
from deepdiff.helper import JSON, SummaryNodeType
from deepdiff.serialization import json_dumps


def _truncate(s: str, max_len: int) -> str:
    """
    Truncate string s to max_len characters.
    If possible, keep the first (max_len-5) characters, then '...' then the last 2 characters.
    """
    if len(s) <= max_len:
        return s
    if max_len <= 5:
        return s[:max_len]
    return s[:max_len - 5] + "..." + s[-2:]
# Re-defining the functions due to environment reset


# Function to calculate node weights recursively
def calculate_weights(node):
    if isinstance(node, dict):
        weight = 0
        children_weights = {}
        for k, v in node.items():
            try:
                edge_weight = len(k)
            except TypeError:
                edge_weight = 1
            child_weight, child_structure = calculate_weights(v)
            total_weight = edge_weight + child_weight
            weight += total_weight
            children_weights[k] = (edge_weight, child_weight, child_structure)
        return weight, (SummaryNodeType.dict, children_weights)

    elif isinstance(node, list):
        weight = 0
        children_weights = []
        for v in node:
            edge_weight = 0  # Index weights are zero
            child_weight, child_structure = calculate_weights(v)
            total_weight = edge_weight + child_weight
            weight += total_weight
            children_weights.append((edge_weight, child_weight, child_structure))
        return weight, (SummaryNodeType.list, children_weights)

    else:
        if isinstance(node, str):
            node_weight = len(node)
        elif isinstance(node, int):
            node_weight = len(str(node))
        elif isinstance(node, float):
            node_weight = len(str(round(node, 2)))
        elif node is None:
            node_weight = 1
        else:
            node_weight = 0
        return node_weight, (SummaryNodeType.leaf, node)

# Include previously defined functions for shrinking with threshold
# (Implementing directly the balanced summarization algorithm as above)

# Balanced algorithm (simplified version):
def shrink_tree_balanced(node_structure, max_weight: int, balance_threshold: float) -> Tuple[JSON, float]:
    node_type, node_info = node_structure

    if node_type is SummaryNodeType.leaf:
        leaf_value = node_info
        leaf_weight, _ = calculate_weights(leaf_value)
        if leaf_weight <= max_weight:
            return leaf_value, leaf_weight
        else:
            if isinstance(leaf_value, str):
                truncated_value = _truncate(leaf_value, max_weight)
                return truncated_value, len(truncated_value)
            elif isinstance(leaf_value, (int, float)):
                leaf_str = str(leaf_value)
                truncated_str = leaf_str[:max_weight]
                try:
                    return int(truncated_str), len(truncated_str)
                except Exception:
                    try:
                        return float(truncated_str), len(truncated_str)
                    except Exception:
                        return truncated_str, len(truncated_str)
            elif leaf_value is None:
                return None, 1 if max_weight >= 1 else 0

    elif node_type is SummaryNodeType.dict:
        shrunk_dict = {}
        total_weight = 0
        sorted_children = sorted(node_info.items(), key=lambda x: x[1][0] + x[1][1], reverse=True)

        for k, (edge_w, _, child_struct) in sorted_children:
            allowed_branch_weight = min(max_weight * balance_threshold, max_weight - total_weight)
            if allowed_branch_weight <= edge_w:
                continue

            remaining_weight = int(allowed_branch_weight - edge_w)
            shrunk_child, shrunk_weight = shrink_tree_balanced(child_struct, remaining_weight, balance_threshold)
            if shrunk_child is not None:
                shrunk_dict[k[:edge_w]] = shrunk_child
                total_weight += edge_w + shrunk_weight

            if total_weight >= max_weight:
                break
        if not shrunk_dict:
            return None, 0

        return shrunk_dict, total_weight

    elif node_type is SummaryNodeType.list:
        shrunk_list = []
        total_weight = 0
        sorted_children = sorted(node_info, key=lambda x: x[0] + x[1], reverse=True)
        for edge_w, _, child_struct in sorted_children:
            allowed_branch_weight = int(min(max_weight * balance_threshold, max_weight - total_weight))
            shrunk_child, shrunk_weight = shrink_tree_balanced(child_struct, allowed_branch_weight, balance_threshold)
            if shrunk_child is not None:
                shrunk_list.append(shrunk_child)
                total_weight += shrunk_weight
            if total_weight >= max_weight - 1:
                shrunk_list.append("...")
                break
        if not shrunk_list:
            return None, 0
        return shrunk_list, total_weight
    return None, 0


def greedy_tree_summarization_balanced(json_data: JSON, max_weight: int, balance_threshold=0.6) -> JSON:
    total_weight, tree_structure = calculate_weights(json_data)
    if total_weight <= max_weight:
        return json_data
    shrunk_tree, _ = shrink_tree_balanced(tree_structure, max_weight, balance_threshold)
    return shrunk_tree


def summarize(data: JSON, max_length:int=200, balance_threshold:float=0.6) -> str:
    try:
        return json_dumps(
            greedy_tree_summarization_balanced(data, max_length, balance_threshold)
        )
    except Exception:
        return str(data)
