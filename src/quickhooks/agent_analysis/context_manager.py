"""Context management for agent analysis with token-aware chunking."""

import re

from .types import ContextChunk


class ContextManager:
    """Manages context chunking and token estimation for agent analysis."""

    def __init__(self, max_tokens: int = 128000, safety_margin: float = 0.9):
        """
        Initialize the context manager.

        Args:
            max_tokens: Maximum tokens allowed
            safety_margin: Safety margin as percentage (0.9 = 90%)
        """
        self.max_tokens = max_tokens
        self.effective_max = int(max_tokens * safety_margin)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        This is a rough estimate based on the general rule of thumb:
        - 1 token ≈ 4 characters for English text
        - Adjusted for code and technical content

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Basic character-based estimation
        char_count = len(text)

        # Adjust for different content types
        if self._is_code_heavy(text):
            # Code tends to be more token-dense
            return int(char_count / 3.5)
        elif self._is_technical_text(text):
            # Technical text with many technical terms
            return int(char_count / 3.8)
        else:
            # Regular text
            return int(char_count / 4.2)

    def _is_code_heavy(self, text: str) -> bool:
        """Check if text contains a lot of code."""
        code_indicators = [
            r"def\s+\w+\(",  # Python functions
            r"class\s+\w+",  # Class definitions
            r"import\s+\w+",  # Import statements
            r"from\s+\w+\s+import",  # Import statements
            r"\{.*\}",  # Braces
            r"if\s*\(",  # If statements
            r"for\s*\(",  # For loops
            r"while\s*\(",  # While loops
            r"=>",  # Arrow functions
            r"console\.log",  # JavaScript
            r"std::",  # C++
        ]

        matches = sum(1 for pattern in code_indicators if re.search(pattern, text))
        return matches >= 3

    def _is_technical_text(self, text: str) -> bool:
        """Check if text is technical documentation or similar."""
        technical_indicators = [
            r"API",
            r"HTTP",
            r"JSON",
            r"XML",
            r"database",
            r"server",
            r"client",
            r"endpoint",
            r"authentication",
            r"authorization",
        ]

        matches = sum(
            1 for word in technical_indicators if word.lower() in text.lower()
        )
        return matches >= 3

    def chunk_context(self, context: str, prompt: str) -> list[ContextChunk]:
        """
        Chunk context to fit within token limits while preserving important information.

        Strategy:
        1. Always include the full prompt
        2. If context fits within limits, use it all
        3. If not, take chunks from start and end (90% of available space)

        Args:
            context: The full context to chunk
            prompt: The user's prompt (always included)

        Returns:
            List of context chunks to use
        """
        chunks = []
        prompt_tokens = self.estimate_tokens(prompt)
        available_tokens = (
            self.effective_max - prompt_tokens - 500
        )  # Reserve for response

        if not context:
            return chunks

        context_tokens = self.estimate_tokens(context)

        # If context fits, use it all
        if context_tokens <= available_tokens:
            chunks.append(
                ContextChunk(
                    content=context,
                    chunk_type="complete",
                    token_count=context_tokens,
                    position=0,
                )
            )
            return chunks

        # Need to chunk - use 90% strategy
        usable_tokens = int(available_tokens * 0.9)
        start_tokens = usable_tokens // 2
        end_tokens = usable_tokens - start_tokens

        # Get start chunk
        start_chunk = self._get_chunk_by_tokens(context, start_tokens, from_start=True)
        if start_chunk:
            chunks.append(
                ContextChunk(
                    content=start_chunk,
                    chunk_type="start",
                    token_count=self.estimate_tokens(start_chunk),
                    position=0,
                )
            )

        # Get end chunk
        end_chunk = self._get_chunk_by_tokens(context, end_tokens, from_start=False)
        if end_chunk:
            chunks.append(
                ContextChunk(
                    content=end_chunk,
                    chunk_type="end",
                    token_count=self.estimate_tokens(end_chunk),
                    position=len(context) - len(end_chunk),
                )
            )

        return chunks

    def _get_chunk_by_tokens(
        self, text: str, target_tokens: int, from_start: bool = True
    ) -> str:
        """
        Extract a chunk of text with approximately target_tokens.

        Args:
            text: Source text
            target_tokens: Target token count
            from_start: If True, extract from start; if False, from end

        Returns:
            Extracted chunk
        """
        # Estimate characters needed
        target_chars = int(target_tokens * 4)  # Conservative estimate

        if from_start:
            if len(text) <= target_chars:
                return text

            # Find a good breaking point (end of line, sentence, etc.)
            chunk = text[:target_chars]

            # Try to break at a reasonable point
            for break_char in ["\n\n", "\n", ". ", "! ", "? ", "; "]:
                last_break = chunk.rfind(break_char)
                if last_break > target_chars * 0.7:  # Don't break too early
                    return chunk[: last_break + len(break_char)]

            return chunk
        else:
            if len(text) <= target_chars:
                return text

            # Get from end
            chunk = text[-target_chars:]

            # Try to break at a reasonable point from the beginning
            for break_char in ["\n\n", "\n", ". ", "! ", "? ", "; "]:
                first_break = chunk.find(break_char)
                if (
                    first_break != -1 and first_break < target_chars * 0.3
                ):  # Don't break too late
                    return chunk[first_break + len(break_char) :]

            return chunk

    def calculate_total_tokens(self, chunks: list[ContextChunk], prompt: str) -> int:
        """Calculate total tokens for chunks plus prompt."""
        chunk_tokens = sum(chunk.token_count for chunk in chunks)
        prompt_tokens = self.estimate_tokens(prompt)
        return chunk_tokens + prompt_tokens
