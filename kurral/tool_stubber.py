"""
Tool stubbing mechanism for B replay
Intercepts tool calls and returns cached responses from artifact
"""

from typing import Any, Dict, Optional, Callable, Tuple
from datetime import datetime
from kurral.models.kurral import ToolCall, ToolCallStatus


def _calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two texts using multiple methods.
    Returns a score between 0.0 and 1.0.
    
    Args:
        text1: First text to compare
        text2: Second text to compare
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    text1 = str(text1).strip().lower()
    text2 = str(text2).strip().lower()
    
    # Exact match
    if text1 == text2:
        return 1.0
    
    # Calculate Levenshtein distance for better handling of typos
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings"""
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    # Calculate edit distance similarity
    max_len = max(len(text1), len(text2))
    if max_len == 0:
        return 1.0
    
    edit_dist = levenshtein_distance(text1, text2)
    edit_similarity = 1.0 - (edit_dist / max_len)
    
    # Word-level similarity
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if words1 and words2:
        word_intersection = len(words1 & words2)
        word_union = len(words1 | words2)
        word_similarity = word_intersection / word_union if word_union > 0 else 0.0
    else:
        word_similarity = 0.0
    
    # Combine edit distance and word similarity
    combined = (edit_similarity * 0.6) + (word_similarity * 0.4)
    
    return max(0.0, min(1.0, combined))


def _compare_tool_inputs(input1: Dict[str, Any], input2: Dict[str, Any]) -> float:
    """
    Compare two tool input dictionaries and return similarity score.
    
    Args:
        input1: First tool input dict
        input2: Second tool input dict
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    # Convert both to strings for comparison
    def normalize_input(inp: Dict[str, Any]) -> str:
        """Normalize input dict to a comparable string"""
        # Sort keys for consistent comparison
        sorted_items = sorted(inp.items())
        parts = []
        for key, value in sorted_items:
            # Convert value to string and normalize
            val_str = str(value).strip().lower()
            parts.append(f"{key}:{val_str}")
        return " ".join(parts)
    
    str1 = normalize_input(input1)
    str2 = normalize_input(input2)
    
    return _calculate_semantic_similarity(str1, str2)


class ToolStubber:
    """
    Stubs tool calls during B replay by returning cached responses from artifact
    """
    
    def __init__(self, artifact_tool_calls: list[ToolCall], side_effect_config: Optional[Dict[str, Any]] = None):
        """
        Initialize tool stubber with artifact tool calls
        
        Args:
            artifact_tool_calls: List of tool calls from the original artifact
            side_effect_config: Side effect configuration dictionary (optional)
        """
        # Build cache: cache_key -> ToolCall
        self.cache: Dict[str, ToolCall] = {}
        self.used_keys: set[str] = set()
        self.new_tool_calls: list[ToolCall] = []
        self.side_effect_config = side_effect_config or {}
        
        for tc in artifact_tool_calls:
            if tc.cache_key:
                self.cache[tc.cache_key] = tc
    
    def stub_tool_call(self, tool_name: str, tool_input: Dict[str, Any], similarity_threshold: float = 0.85) -> Optional[Tuple[Dict[str, Any], str, float]]:
        """
        Check if tool call matches cached result using semantic similarity.
        This is called BEFORE executing the tool - A/B testing logic.
        
        For side effect tools (marked as False in config), always returns cached result
        or safe default - never returns None to prevent execution.
        
        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters to the tool
            similarity_threshold: Minimum similarity score to consider a match (default: 0.85)
            
        Returns:
            Tuple of (cached output, cache_key, similarity_score) if similarity >= threshold, None otherwise
            For side effect tools, always returns a result (cached or safe default)
        """
        # Check if this is a side effect tool
        from kurral.side_effect_config import SideEffectConfig
        is_side_effect = SideEffectConfig.is_side_effect(self.side_effect_config, tool_name)
        
        # First, try exact match
        cache_key = ToolCall.generate_cache_key(tool_name, tool_input)
        
        if cache_key in self.cache:
            # Exact match found - CACHE HIT (similarity = 1.0)
            cached_tc = self.cache[cache_key]
            self.used_keys.add(cache_key)
            return (cached_tc.output if cached_tc.output else {}, cache_key, 1.0)
        
        # No exact match - try semantic similarity matching
        # IMPORTANT: Only search through unused tool calls to avoid double-matching
        best_match: Optional[Tuple[ToolCall, float, str]] = None
        best_similarity = 0.0
        
        for cached_key, cached_tc in self.cache.items():
            # Skip if already used (each tool call should only be matched once)
            if cached_key in self.used_keys:
                continue
            
            # Only compare if tool names match
            if cached_tc.tool_name != tool_name:
                continue
            
            # Compare inputs using semantic similarity
            similarity = _compare_tool_inputs(tool_input, cached_tc.input)
            
            if similarity >= similarity_threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = (cached_tc, similarity, cached_key)
        
        if best_match:
            # Found semantically similar match (similarity >= threshold)
            # CACHE HIT: Return cached output, tool should NOT be executed
            cached_tc, similarity, matched_key = best_match
            self.used_keys.add(matched_key)
            return (cached_tc.output if cached_tc.output else {}, matched_key, similarity)
        else:
            # Not similar enough (similarity < threshold) - CACHE MISS
            if is_side_effect:
                # Side effect tool with no cache - return safe default
                safe_default = {
                    "status": "blocked",
                    "message": f"Side effect tool '{tool_name}' blocked during replay (no cached result available)"
                }
                return (safe_default, "", 0.0)
            else:
                # Normal tool - can be executed in real-time
                return None
    
    def get_unused_tool_calls(self) -> list[ToolCall]:
        """Get tool calls from artifact that weren't used during replay"""
        unused = []
        for cache_key, tc in self.cache.items():
            if cache_key not in self.used_keys:
                unused.append(tc)
        return unused
    
    def record_new_tool_call(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        tool_output: Dict[str, Any],
        outside_original: bool = True
    ) -> ToolCall:
        """
        Record a new tool call that wasn't in the original artifact
        
        Args:
            tool_name: Name of the tool
            tool_input: Input parameters
            tool_output: Output from the tool
            outside_original: Whether this was outside the original artifact
            
        Returns:
            ToolCall object
        """
        cache_key = ToolCall.generate_cache_key(tool_name, tool_input)
        
        tool_call = ToolCall(
            tool_name=tool_name,
            input=tool_input,
            output=tool_output,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            latency_ms=0,
            status=ToolCallStatus.OK,
            cache_key=cache_key,
            stubbed_in_replay=False,
            metadata={"outside_original_artifact": outside_original} if outside_original else {}
        )
        
        self.new_tool_calls.append(tool_call)
        return tool_call


def create_stubbed_tool(original_func: Callable, stubber: ToolStubber, tool_name: str, side_effect_config: Optional[Dict[str, Any]] = None) -> Callable:
    """
    Create a stubbed version of a tool function
    
    Args:
        original_func: Original tool function
        stubber: ToolStubber instance
        tool_name: Name of the tool
        side_effect_config: Side effect configuration dictionary (optional)
        
    Returns:
        Stubbed function that checks cache first, then calls original if not cached
        For side effect tools, always uses cache or safe default, never executes
    """
    def stubbed_func(*args, **kwargs):
        # Convert args/kwargs to input dict (matching artifact format)
        tool_input = {}
        
        # LangChain tools typically pass input as a single string argument
        if args:
            if len(args) == 1:
                arg = args[0]
                # Match artifact format: {"input": "value"}
                tool_input = {"input": arg}
            else:
                tool_input = {"args": list(args)}
        
        # Add any kwargs
        tool_input.update(kwargs)
        
        # A/B TESTING LOGIC: Check semantic similarity BEFORE calling the tool
        # If similarity >= 85%: CACHE HIT - return cached result, DO NOT call tool
        # If similarity < 85%: CACHE MISS - call the tool in real-time
        cache_result = stubber.stub_tool_call(tool_name, tool_input, similarity_threshold=0.85)
        
        if cache_result is not None:
            # CACHE HIT: Similarity >= 85% with a cached tool call
            # Return cached output immediately, DO NOT execute the tool
            cached_output, matched_key, similarity_score = cache_result
            
            # Log cache hit (only count as cache hit when we actually use cached output)
            print(f"\n[CACHE HIT] {tool_name}({tool_input}) - Similarity: {similarity_score:.2f} >= 0.85, using cached result")
            
            # Extract the actual output value
            if isinstance(cached_output, dict):
                if "output" in cached_output:
                    return cached_output["output"]
                # Otherwise return the dict (might be the output itself)
                return cached_output
            else:
                return cached_output
        else:
            # CACHE MISS: Similarity < 85% or no cached match found
            # Check if this is a side effect tool
            from kurral.side_effect_config import SideEffectConfig
            is_side_effect = SideEffectConfig.is_side_effect(side_effect_config or {}, tool_name)
            
            if is_side_effect:
                # Side effect tool - return safe default, DO NOT execute
                safe_default = {
                    "status": "blocked",
                    "message": f"Side effect tool '{tool_name}' blocked during replay (no cached result available)"
                }
                print(f"\n[SIDE EFFECT BLOCKED] {tool_name}({tool_input}) - Side effect tool blocked, returning safe default")
                return safe_default
            else:
                # Normal tool - execute in real-time (this is a new tool call)
                print(f"\n[CACHE MISS] {tool_name}({tool_input}) - No match found or similarity < 0.85, executing tool")
                result = original_func(*args, **kwargs)
                
                # Record as new tool call (cache miss - executed in real-time)
                output_dict = {"output": result} if not isinstance(result, dict) else result
                stubber.record_new_tool_call(tool_name, tool_input, output_dict, outside_original=True)
                
                return result
    
    return stubbed_func

