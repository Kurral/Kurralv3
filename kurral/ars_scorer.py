"""
ARS (Agent Regression Score) Calculator
Calculates regression score based on output similarity and tool call accuracy
"""

from typing import Any, Dict, List
from kurral.models.kurral import ToolCall


def calculate_ars(
    original_outputs: Dict[str, Any],
    replayed_outputs: Dict[str, Any],
    original_tool_calls: List[ToolCall],
    replayed_tool_calls: List[ToolCall],
    new_tool_calls: List[ToolCall],
    unused_tool_calls: List[ToolCall],
) -> Dict[str, Any]:
    """
    Calculate Agent Regression Score (ARS)
    
    ARS is calculated based on:
    1. Output similarity (semantic/text similarity between outputs)
    2. Tool call accuracy (matches, misses, new calls)
    
    Ideal score: 1.0 (perfect match)
    
    Args:
        original_outputs: Original outputs from artifact
        replayed_outputs: Replayed outputs
        original_tool_calls: Original tool calls from artifact
        replayed_tool_calls: Tool calls from replay
        new_tool_calls: New tool calls not in original artifact
        unused_tool_calls: Tool calls from artifact that weren't used
        
    Returns:
        Dict with ARS score and breakdown
    """
    # Extract interaction outputs
    original_interactions = original_outputs.get("interactions", [])
    replayed_interactions = replayed_outputs.get("interactions", [])
    
    # If not in interactions format, treat as single output
    if not original_interactions:
        # Check if it's a dict with 'output' key (single interaction format)
        if isinstance(original_outputs, dict) and "output" in original_outputs:
            original_interactions = [original_outputs]
        else:
            original_interactions = [original_outputs]
    if not replayed_interactions:
        # Check if it's a dict with 'output' key (single interaction format)
        if isinstance(replayed_outputs, dict) and "output" in replayed_outputs:
            replayed_interactions = [replayed_outputs]
        else:
            replayed_interactions = [replayed_outputs]
    
    # Calculate output similarity score
    output_scores = []
    for orig, replayed in zip(original_interactions, replayed_interactions):
        orig_output = _extract_output(orig)
        replayed_output = _extract_output(replayed)
        similarity = _calculate_text_similarity(orig_output, replayed_output)
        output_scores.append(similarity)
    
    # Average output similarity
    output_score = sum(output_scores) / len(output_scores) if output_scores else 0.0
    
    # Calculate tool call accuracy
    total_original_tools = len(original_tool_calls)
    total_replayed_tools = len(replayed_tool_calls)
    new_tools_count = len(new_tool_calls)
    unused_tools_count = len(unused_tool_calls)
    
    # Tool call match score
    # Perfect if: all original tools used, no new tools, no unused tools
    if total_original_tools == 0:
        # No tools in original - perfect if no tools in replay either
        tool_score = 1.0 if total_replayed_tools == 0 else 0.5
    else:
        # Calculate based on:
        # - Used original tools: (total_original - unused) / total_original
        # - Penalty for new tools: -0.1 per new tool (capped at -0.5)
        # - Penalty for unused tools: -0.1 per unused tool (capped at -0.5)
        used_original = total_original_tools - unused_tools_count
        used_ratio = used_original / total_original_tools if total_original_tools > 0 else 0.0
        
        new_penalty = min(0.5, new_tools_count * 0.1)
        unused_penalty = min(0.5, unused_tools_count * 0.1)
        
        tool_score = max(0.0, used_ratio - new_penalty - unused_penalty)
    
    # Overall ARS: weighted average (70% output, 30% tools)
    ars_score = (output_score * 0.7) + (tool_score * 0.3)
    
    return {
        "ars_score": round(ars_score, 4),
        "output_similarity": round(output_score, 4),
        "tool_accuracy": round(tool_score, 4),
        "breakdown": {
            "output_scores": [round(s, 4) for s in output_scores],
            "total_original_tools": total_original_tools,
            "total_replayed_tools": total_replayed_tools,
            "used_original_tools": total_original_tools - unused_tools_count,
            "new_tools": new_tools_count,
            "unused_tools": unused_tools_count,
        }
    }


def _extract_output(interaction: Dict[str, Any]) -> str:
    """Extract output text from interaction dict"""
    if isinstance(interaction, dict):
        if "output" in interaction:
            return str(interaction["output"])
        elif "error" in interaction:
            return f"ERROR: {interaction['error']}"
        else:
            # Try to find any string value
            for v in interaction.values():
                if isinstance(v, str):
                    return v
    return str(interaction)


def _calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts
    Uses exact match first, then simple string similarity
    """
    text1 = str(text1).strip().lower()
    text2 = str(text2).strip().lower()
    
    # Exact match
    if text1 == text2:
        return 1.0
    
    # Check if one contains the other (partial match)
    if text1 in text2 or text2 in text1:
        # Calculate containment ratio
        shorter = min(len(text1), len(text2))
        longer = max(len(text1), len(text2))
        if longer > 0:
            return shorter / longer
    
    # Simple character-based similarity (Jaccard-like)
    # Compare character sets
    set1 = set(text1)
    set2 = set(text2)
    
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 1.0
    
    jaccard = intersection / union
    
    # Also consider word overlap for better semantic similarity
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if words1 and words2:
        word_intersection = len(words1 & words2)
        word_union = len(words1 | words2)
        word_similarity = word_intersection / word_union if word_union > 0 else 0.0
    else:
        word_similarity = 0.0
    
    # Combine character and word similarity
    combined = (jaccard * 0.5) + (word_similarity * 0.5)
    
    return max(0.0, min(1.0, combined))

