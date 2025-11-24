"""
Default configuration for Kurral replay system
Provides default LLM parameters when not specified in artifact
"""

from typing import Optional
from Kurral_tester.models.kurral import LLMParameters, ModelConfig


# Default LLM parameters (used when not in artifact)
DEFAULT_LLM_PARAMETERS = LLMParameters(
    temperature=0.0,
    seed=42,
    top_p=None,
    top_k=None,
    max_tokens=None,
    frequency_penalty=None,
    presence_penalty=None,
)


def get_llm_parameters_from_artifact(
    artifact_config: Optional[ModelConfig],
) -> LLMParameters:
    """
    Get LLM parameters from artifact, or use defaults if not present
    
    Args:
        artifact_config: ModelConfig from artifact (may be None)
        
    Returns:
        LLMParameters with values from artifact or defaults
    """
    if artifact_config and artifact_config.parameters:
        params = artifact_config.parameters
        return LLMParameters(
            temperature=params.temperature if params.temperature is not None else DEFAULT_LLM_PARAMETERS.temperature,
            seed=params.seed if params.seed is not None else DEFAULT_LLM_PARAMETERS.seed,
            top_p=params.top_p if params.top_p is not None else DEFAULT_LLM_PARAMETERS.top_p,
            top_k=params.top_k if params.top_k is not None else DEFAULT_LLM_PARAMETERS.top_k,
            max_tokens=params.max_tokens if params.max_tokens is not None else DEFAULT_LLM_PARAMETERS.max_tokens,
            frequency_penalty=params.frequency_penalty if params.frequency_penalty is not None else DEFAULT_LLM_PARAMETERS.frequency_penalty,
            presence_penalty=params.presence_penalty if params.presence_penalty is not None else DEFAULT_LLM_PARAMETERS.presence_penalty,
        )
    else:
        return DEFAULT_LLM_PARAMETERS

