"""
LLM adapter for code generation with fallback to deterministic behavior.

Supports:
- OpenAI API (GPT-4, GPT-3.5-turbo)
- Anthropic API (Claude)
- Graceful fallback to deterministic patches when LLM unavailable
"""

import os
import importlib
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMCodeGenRequest:
    """Request for LLM-based code generation."""
    file_path: str
    current_content: str
    objective: str  # E.g., "Fix login validation", "Add error handling"
    context: str  # Additional context (test failures, requirements)
    language: str = "python"


@dataclass
class LLMCodeGenResponse:
    """Response from LLM code generation."""
    success: bool
    generated_code: Optional[str] = None
    error_message: Optional[str] = None
    model_used: Optional[str] = None


class LLMCodeGenerator:
    """
    Generate code patches using LLM APIs with graceful fallback.
    
    Initialization:
    - Set LLM_API_KEY environment variable (OpenAI or Anthropic)
    - Set LLM_API_PROVIDER to "openai" or "anthropic" (default: "openai")
    - Set LLM_MODEL to specify model (default: "gpt-4" for OpenAI, "claude-3-opus" for Anthropic)
    
    If LLM_API_KEY is not set, all calls return success=False and should trigger fallback.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ):
        """
        Initialize LLM code generator.
        
        Args:
            api_key: LLM API key (OpenAI or Anthropic). If None, reads from LLM_API_KEY env.
            provider: "openai" or "anthropic". Default from LLM_API_PROVIDER env or "openai".
            model: Model name. Default from LLM_MODEL env or provider default.
            temperature: Sampling temperature (0.0-1.0). Default 0.3 for deterministic output.
        """
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.provider = (provider or os.environ.get("LLM_API_PROVIDER", "openai")).lower()
        self.temperature = temperature
        
        if self.provider == "openai":
            self.model = model or os.environ.get("LLM_MODEL", "gpt-4")
        elif self.provider == "anthropic":
            self.model = model or os.environ.get("LLM_MODEL", "claude-3-opus-20240229")
        else:
            self.model = model or "gpt-4"
        
        self.available = bool(self.api_key)
        if not self.available:
            logger.debug(
                "LLM code generation disabled: LLM_API_KEY not set. "
                "Set LLM_API_KEY environment variable to enable LLM-based patch generation."
            )
    
    def generate_function_replacement(
        self,
        source_code: str,
        function_name: str,
        objective: str,
        file_path: str,
    ) -> LLMCodeGenResponse:
        """
        Generate a replacement for a specific function.
        
        Args:
            source_code: Complete source file content
            function_name: Name of function to replace
            objective: Description of desired changes (e.g., "Fix authentication bypass")
            file_path: Path to the source file (for context)
        
        Returns:
            LLMCodeGenResponse with generated function or fallback indication
        """
        if not self.available:
            logger.debug(f"LLM generation skipped for {function_name}: LLM disabled")
            return LLMCodeGenResponse(
                success=False,
                error_message="LLM not configured (LLM_API_KEY not set)",
            )
        
        prompt = self._build_function_generation_prompt(
            source_code,
            function_name,
            objective,
            file_path,
        )
        
        return self._call_llm(prompt, objective)
    
    def generate_file_content(
        self,
        file_path: str,
        current_content: str,
        objective: str,
        context: str = "",
    ) -> LLMCodeGenResponse:
        """
        Generate complete file content with modifications.
        
        Args:
            file_path: Path to the file being modified
            current_content: Current file content
            objective: Description of changes needed
            context: Additional context (test failures, requirements)
        
        Returns:
            LLMCodeGenResponse with generated content or fallback indication
        """
        if not self.available:
            logger.debug(f"LLM generation skipped for {file_path}: LLM disabled")
            return LLMCodeGenResponse(
                success=False,
                error_message="LLM not configured (LLM_API_KEY not set)",
            )
        
        prompt = self._build_file_generation_prompt(
            file_path,
            current_content,
            objective,
            context,
        )
        
        return self._call_llm(prompt, objective)
    
    def _build_function_generation_prompt(
        self,
        source_code: str,
        function_name: str,
        objective: str,
        file_path: str,
    ) -> str:
        """Build a prompt for function-level generation."""
        return f"""You are an expert Python code generator. Generate a corrected version of the '{function_name}' function.

**Objective**: {objective}

**File**: {file_path}

**Current source code**:
```python
{source_code}
```

**Task**: 
1. Analyze the current {function_name} function
2. Apply changes that directly address the objective
3. Keep all other functions unchanged
4. Return ONLY valid Python code for the function
5. Include proper error handling and edge cases
6. Preserve the function signature and return type

**Generated function** (Python code only, no markdown, no explanation):"""

    def _build_file_generation_prompt(
        self,
        file_path: str,
        current_content: str,
        objective: str,
        context: str,
    ) -> str:
        """Build a prompt for file-level generation."""
        context_section = f"\n**Context**: {context}" if context else ""
        
        return f"""You are an expert Python code generator. Modify the file to address the objective.

**File**: {file_path}
**Objective**: {objective}{context_section}

**Current content**:
```python
{current_content}
```

**Task**:
1. Analyze why the current code may not meet the objective
2. Make minimal, targeted modifications
3. Preserve all functions and structure not directly related to the objective
4. Ensure proper error handling and validation
5. Maintain backward compatibility where possible
6. Return ONLY valid Python code, no markdown or explanation

**Modified file** (Python code only):"""

    def _call_llm(self, prompt: str, objective: str) -> LLMCodeGenResponse:
        """Call the configured LLM API."""
        try:
            if self.provider == "openai":
                return self._call_openai(prompt, objective)
            elif self.provider == "anthropic":
                return self._call_anthropic(prompt, objective)
            else:
                return LLMCodeGenResponse(
                    success=False,
                    error_message=f"Unknown LLM provider: {self.provider}",
                )
        except Exception as e:
            logger.warning(f"LLM call failed for '{objective}': {e}")
            return LLMCodeGenResponse(
                success=False,
                error_message=f"LLM request failed: {str(e)[:200]}",
            )
    
    def _call_openai(self, prompt: str, objective: str) -> LLMCodeGenResponse:
        """Call OpenAI API."""
        try:
            openai = importlib.import_module("openai")
        except ImportError:
            return LLMCodeGenResponse(
                success=False,
                error_message="openai package not installed. Install with: pip install openai",
            )
        
        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Python developer. Generate only valid Python code. "
                            "Do not include markdown formatting, explanations, or code blocks. "
                            "Output the code directly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=4000,
            )
            
            generated_code = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if generated_code.startswith("```"):
                generated_code = "\n".join(
                    line for line in generated_code.split("\n")
                    if not line.startswith("```")
                ).strip()
            
            return LLMCodeGenResponse(
                success=True,
                generated_code=generated_code,
                model_used=self.model,
            )
        except Exception as e:
            return LLMCodeGenResponse(
                success=False,
                error_message=f"OpenAI API error: {str(e)[:200]}",
            )
    
    def _call_anthropic(self, prompt: str, objective: str) -> LLMCodeGenResponse:
        """Call Anthropic Claude API."""
        try:
            anthropic = importlib.import_module("anthropic")
        except ImportError:
            return LLMCodeGenResponse(
                success=False,
                error_message="anthropic package not installed. Install with: pip install anthropic",
            )
        
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            
            generated_code = response.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if generated_code.startswith("```"):
                generated_code = "\n".join(
                    line for line in generated_code.split("\n")
                    if not line.startswith("```")
                ).strip()
            
            return LLMCodeGenResponse(
                success=True,
                generated_code=generated_code,
                model_used=self.model,
            )
        except Exception as e:
            return LLMCodeGenResponse(
                success=False,
                error_message=f"Anthropic API error: {str(e)[:200]}",
            )
