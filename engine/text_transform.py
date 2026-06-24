"""
RNV Text Transformer - Text Transformer Module
Handles all text transformation operations

Python 3.13 Optimized:
- Match statement for cleaner mode dispatch
- StrEnum for better string enum handling
- Modern type hints
- Pre-compiled regex patterns for performance

"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import ClassVar, Pattern


class TransformMode(StrEnum):
    """
    Available text transformation modes.
    
    Using StrEnum (Python 3.11+) for direct string comparison.
    """
    # Original modes
    UPPERCASE = "UPPERCASE"
    LOWERCASE = "lowercase"
    TITLE_CASE = "Title Case"
    SENTENCE_CASE = "Sentence case"
    
    # Developer-focused modes
    CAMEL_CASE = "camelCase"
    PASCAL_CASE = "PascalCase"
    SNAKE_CASE = "snake_case"
    CONSTANT_CASE = "CONSTANT_CASE"
    KEBAB_CASE = "kebab-case"
    DOT_CASE = "dot.case"
    INVERTED_CASE = "iNVERTED cASE"


class TextTransformer:
    """
    Handles text transformation operations.
    
    Uses pre-compiled regex patterns for optimal performance on large texts.
    """
    
    __slots__ = ()  # No instance attributes needed
    
    # Pre-compiled regex patterns (class-level for reuse)
    # Sentence case patterns
    _SENTENCE_END_PATTERN: ClassVar[Pattern[str]] = re.compile(r'([.!?])\s+([a-z])')
    _NEWLINE_PATTERN: ClassVar[Pattern[str]] = re.compile(r'(\n\s*)([a-z])')
    
    # Word boundary detection patterns for case conversion
    # Matches: camelCase boundaries, PascalCase boundaries, snake_case, kebab-case, dot.case, spaces
    _WORD_BOUNDARY_PATTERN: ClassVar[Pattern[str]] = re.compile(
        r'''
        # camelCase boundary: lowercase followed by uppercase
        (?<=[a-z])(?=[A-Z])
        |
        # PascalCase boundary: uppercase followed by uppercase+lowercase (e.g., "XMLParser" -> "XML", "Parser")
        (?<=[A-Z])(?=[A-Z][a-z])
        |
        # Delimiter boundaries: underscore, hyphen, dot, or whitespace
        [_\-.\s]+
        ''',
        re.VERBOSE
    )
    
    # Pattern to detect if text contains delimiters (for smart detection)
    _HAS_DELIMITERS_PATTERN: ClassVar[Pattern[str]] = re.compile(r'[_\-.\s]')
    
    # Pattern to clean multiple spaces
    _MULTI_SPACE_PATTERN: ClassVar[Pattern[str]] = re.compile(r'\s+')
    
    @staticmethod
    def transform_text(text: str, mode: str) -> str:
        """
        Transform text based on the selected mode.
        
        Uses Python 3.10+ match statement for cleaner dispatch.
        
        Args:
            text: Input text to transform
            mode: Transformation mode (from TransformMode enum)
        
        Returns:
            Transformed text
        """
        # Use match statement for cleaner dispatch
        match mode:
            # Original modes
            case TransformMode.UPPERCASE:
                return text.upper()
            case TransformMode.LOWERCASE:
                return text.lower()
            case TransformMode.TITLE_CASE:
                return text.title()
            case TransformMode.SENTENCE_CASE:
                return TextTransformer._sentence_case(text)
            
            # New developer-focused modes
            case TransformMode.CAMEL_CASE:
                return TextTransformer._to_camel_case(text)
            case TransformMode.PASCAL_CASE:
                return TextTransformer._to_pascal_case(text)
            case TransformMode.SNAKE_CASE:
                return TextTransformer._to_snake_case(text)
            case TransformMode.CONSTANT_CASE:
                return TextTransformer._to_constant_case(text)
            case TransformMode.KEBAB_CASE:
                return TextTransformer._to_kebab_case(text)
            case TransformMode.DOT_CASE:
                return TextTransformer._to_dot_case(text)
            case TransformMode.INVERTED_CASE:
                return TextTransformer._to_inverted_case(text)
            
            case _:
                # Return unchanged for unknown modes
                return text
    
    # ==================== ORIGINAL TRANSFORM METHODS ====================
    
    @staticmethod
    def _sentence_case(text: str) -> str:
        """
        Convert text to sentence case.
        
        Capitalizes the first letter of each sentence while making the rest lowercase.
        Handles multiple sentences separated by . ! ? and preserves paragraph breaks.
        Uses pre-compiled patterns for better performance on large texts.
        
        Args:
            text: Input text
            
        Returns:
            Text in sentence case
        """
        if not text:
            return text
        
        # First, convert everything to lowercase
        result = text.lower()
        
        # Capitalize the first character of the text
        if result:
            result = result[0].upper() + result[1:]
        
        # Capitalize first letter after sentence-ending punctuation
        # Using pre-compiled pattern and f-string in lambda
        result = TextTransformer._SENTENCE_END_PATTERN.sub(
            lambda m: f"{m.group(1)} {m.group(2).upper()}",
            result
        )
        
        # Handle newlines - capitalize first letter after newline(s)
        result = TextTransformer._NEWLINE_PATTERN.sub(
            lambda m: f"{m.group(1)}{m.group(2).upper()}",
            result
        )
        
        return result
    
    # ==================== DEVELOPER TRANSFORM METHODS ====================
    
    @staticmethod
    def _extract_words(text: str) -> list[str]:
        """
        Extract words from text, handling multiple input formats.
        
        Intelligently splits on:
        - Whitespace
        - Underscores (snake_case)
        - Hyphens (kebab-case)
        - Dots (dot.case)
        - camelCase boundaries
        - PascalCase boundaries
        
        Args:
            text: Input text in any format
            
        Returns:
            List of individual words (lowercase)
        """
        if not text:
            return []
        
        # Split on word boundaries
        words = TextTransformer._WORD_BOUNDARY_PATTERN.split(text)
        
        # Filter out empty strings and convert to lowercase
        return [word.lower() for word in words if word]
    
    @staticmethod
    def _to_camel_case(text: str) -> str:
        """
        Convert text to camelCase.
        
        Example: "hello world" -> "helloWorld"
        Example: "Hello_World" -> "helloWorld"
        
        Args:
            text: Input text
            
        Returns:
            Text in camelCase
        """
        words = TextTransformer._extract_words(text)
        
        if not words:
            return ""
        
        # First word lowercase, rest capitalized
        result = words[0]
        for word in words[1:]:
            result += word.capitalize()
        
        return result
    
    @staticmethod
    def _to_pascal_case(text: str) -> str:
        """
        Convert text to PascalCase.
        
        Example: "hello world" -> "HelloWorld"
        Example: "hello_world" -> "HelloWorld"
        
        Args:
            text: Input text
            
        Returns:
            Text in PascalCase
        """
        words = TextTransformer._extract_words(text)
        
        if not words:
            return ""
        
        # All words capitalized
        return ''.join(word.capitalize() for word in words)
    
    @staticmethod
    def _to_snake_case(text: str) -> str:
        """
        Convert text to snake_case.
        
        Example: "Hello World" -> "hello_world"
        Example: "helloWorld" -> "hello_world"
        
        Args:
            text: Input text
            
        Returns:
            Text in snake_case
        """
        words = TextTransformer._extract_words(text)
        
        if not words:
            return ""
        
        return '_'.join(words)
    
    @staticmethod
    def _to_constant_case(text: str) -> str:
        """
        Convert text to CONSTANT_CASE (screaming snake case).
        
        Example: "hello world" -> "HELLO_WORLD"
        Example: "helloWorld" -> "HELLO_WORLD"
        
        Args:
            text: Input text
            
        Returns:
            Text in CONSTANT_CASE
        """
        words = TextTransformer._extract_words(text)
        
        if not words:
            return ""
        
        return '_'.join(word.upper() for word in words)
    
    @staticmethod
    def _to_kebab_case(text: str) -> str:
        """
        Convert text to kebab-case.
        
        Example: "Hello World" -> "hello-world"
        Example: "HelloWorld" -> "hello-world"
        
        Args:
            text: Input text
            
        Returns:
            Text in kebab-case
        """
        words = TextTransformer._extract_words(text)
        
        if not words:
            return ""
        
        return '-'.join(words)
    
    @staticmethod
    def _to_dot_case(text: str) -> str:
        """
        Convert text to dot.case.
        
        Example: "Hello World" -> "hello.world"
        Example: "HelloWorld" -> "hello.world"
        
        Args:
            text: Input text
            
        Returns:
            Text in dot.case
        """
        words = TextTransformer._extract_words(text)
        
        if not words:
            return ""
        
        return '.'.join(words)
    
    @staticmethod
    def _to_inverted_case(text: str) -> str:
        """
        Convert text to iNVERTED cASE (swap case of each character).
        
        Example: "Hello World" -> "hELLO wORLD"
        Example: "HELLO" -> "hello"
        
        Args:
            text: Input text
            
        Returns:
            Text with inverted case
        """
        return text.swapcase()
    
    # ==================== UTILITY METHODS ====================
    
    @staticmethod
    def get_available_modes() -> list[str]:
        """
        Get list of available transformation modes.
        
        Returns:
            List of mode display names
        """
        return [mode.value for mode in TransformMode]
    
    @staticmethod
    def get_mode_by_name(name: str) -> TransformMode | None:
        """
        Get TransformMode enum by display name.
        
        Args:
            name: Mode display name
            
        Returns:
            TransformMode enum or None if not found
        """
        for mode in TransformMode:
            if mode.value == name:
                return mode
        return None
    
    @staticmethod
    def get_original_modes() -> list[str]:
        """
        Get list of basic transformation modes (case-only variants).
        
        Returns:
            List of original mode display names
        """
        return [
            TransformMode.UPPERCASE.value,
            TransformMode.LOWERCASE.value,
            TransformMode.TITLE_CASE.value,
            TransformMode.SENTENCE_CASE.value,
        ]
    
    @staticmethod
    def get_developer_modes() -> list[str]:
        """
        Get list of developer-focused transformation modes.
        
        Returns:
            List of developer mode display names
        """
        return [
            TransformMode.CAMEL_CASE.value,
            TransformMode.PASCAL_CASE.value,
            TransformMode.SNAKE_CASE.value,
            TransformMode.CONSTANT_CASE.value,
            TransformMode.KEBAB_CASE.value,
            TransformMode.DOT_CASE.value,
            TransformMode.INVERTED_CASE.value,
        ]