"""
Deep Extraction Module for RenLocalizer v2.7.1

Provides shared configuration, heuristics, and utilities for extracting
translatable strings from non-standard Ren'Py patterns:
  - Bare define/default strings (without _() wrapper)
  - Complex data structures (dicts, lists) in define/default
  - f-string template extraction
  - Extended Ren'Py API call coverage
  - Variable name heuristic scoring

Used by both parser.py (.rpy files) and rpyc_reader.py (.rpyc files).
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# DEEP EXTRACTION CONFIGURATION
# =============================================================================

class DeepExtractionConfig:
    """Central configuration for deep extraction across parser and RPYC reader."""

    # -------------------------------------------------------------------------
    # Tier-1: Functions where specific arguments ALWAYS contain user-facing text
    # Format: func_name -> {"pos": [positional_indices], "kw": [keyword_arg_names]}
    # -------------------------------------------------------------------------
    TIER1_TEXT_CALLS: Dict[str, Dict[str, list]] = {
        # Direct text display
        "renpy.notify":         {"pos": [0]},
        "renpy.confirm":        {"pos": [0]},
        "renpy.say":            {"pos": [1]},           # what parameter (2nd arg)
        "renpy.input":          {"pos": [0], "kw": ["prompt", "default"]},
        "renpy.display_notify": {"pos": [0]},
        # Screen Actions
        "Confirm":              {"pos": [0]},            # prompt
        "Notify":               {"pos": [0]},            # message
        "Tooltip":              {"pos": [0]},            # default value
        "MouseTooltip":         {"pos": [0]},
        # UI constructors
        "Character":            {"pos": [0]},            # name
        "DynamicCharacter":     {"pos": [0]},
        "Text":                 {"pos": [0]},
        "ui.text":              {"pos": [0]},
        "ui.textbutton":        {"pos": [0]},
        "ui.label":             {"pos": [0]},
        # Game systems
        "achievement.register": {"pos": [0], "kw": ["stat_name"]},
        # Character proxy / narrator
        "narrator":             {"pos": [0]},
        # Gallery / Interface (v2.7.2 Enhancement)
        "gallery.button":       {"pos": [0]},
        "gallery_gup.button":   {"pos": [0]}, # Specific to Oyun5 but common pattern
        "unlock_image":         {"pos": [0]},
        "image":                {"pos": [0], "kw": ["message"]}, # Context-aware in Gallery
    }

    # -------------------------------------------------------------------------
    # Tier-2: Functions with contextual text arguments (need careful extraction)
    # -------------------------------------------------------------------------
    TIER2_CONTEXTUAL_CALLS: Dict[str, Dict[str, list]] = {
        "QuickSave":                {"kw": ["message"]},
        "CopyToClipboard":         {"pos": [0]},
        "FilePageNameInputValue":  {"kw": ["pattern", "auto", "quick"]},
        "Help":                    {"pos": [0]},
    }

    # -------------------------------------------------------------------------
    # Tier-3: Functions whose arguments should NEVER be extracted (blacklist)
    # -------------------------------------------------------------------------
    TIER3_BLACKLIST_CALLS: Set[str] = {
        # Navigation / flow
        "Jump", "Call", "Return", "Show", "Hide", "ShowTransient",
        "ToggleScreen", "ShowMenu",
        # Audio
        "Play", "Queue", "Stop", "SetMixer",
        # Variable manipulation
        "SetVariable", "ToggleVariable", "SetField", "SetDict",
        "SetScreenVariable", "SetLocalVariable", "ToggleSetMembership",
        "AddToSet", "RemoveFromSet", "InvertSelected",
        # File operations
        "FileLoad", "FileSave", "FileDelete", "FilePage",
        "FilePageNext", "FilePagePrevious", "FileTakeScreenshot",
        # Settings (first arg is API key, not user text)
        "Preference",
        # URL / technical
        "OpenURL", "StylePreference",
        # Ren'Py API - navigation/technical
        "renpy.jump", "renpy.call", "renpy.show", "renpy.hide",
        "renpy.scene", "renpy.play", "renpy.queue",
        "renpy.music.play", "renpy.music.queue", "renpy.music.stop",
        "renpy.sound.play", "renpy.sound.queue", "renpy.sound.stop",
        "renpy.movie_cutscene", "renpy.transition",
        "renpy.pause", "renpy.show_screen", "renpy.hide_screen",
        "renpy.get_screen", "renpy.get_widget",
    }

    # -------------------------------------------------------------------------
    # Config variable patterns that may carry translatable text
    # -------------------------------------------------------------------------
    CONFIG_TEXT_VARS: Set[str] = {
        "config.name", "config.window_title", "config.help",
        "gui.about", "gui.main_menu_title",
    }

    # Config variables that should NOT be translated
    CONFIG_SKIP_VARS: Set[str] = {
        "config.version", "config.save_directory", "config.window_icon",
        "config.log", "config.developer", "config.default_language",
        "config.searchpath",
    }

    @classmethod
    def get_merged_text_calls(cls, config_manager=None) -> Dict[str, Dict[str, list]]:
        """Return TIER1_TEXT_CALLS merged with user-defined custom_function_params.
        
        User entries override built-in ones (allows customization).
        """
        import json
        merged = dict(cls.TIER1_TEXT_CALLS)
        if config_manager:
            ts = getattr(config_manager, 'translation_settings', None)
            raw = getattr(ts, 'custom_function_params', '{}') if ts else '{}'
            try:
                custom = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(custom, dict):
                    for func_name, params in custom.items():
                        if isinstance(params, dict):
                            merged[func_name] = params
                        elif isinstance(params, list):
                            # Shorthand: ["param1", "param2"] → positional indices
                            merged[func_name] = {"pos": params}
            except (json.JSONDecodeError, TypeError):
                logger.warning("custom_function_params parse error, ignoring")
        return merged

    # -------------------------------------------------------------------------
    # Variable name heuristics for bare define/default extraction
    # -------------------------------------------------------------------------
    TRANSLATABLE_VAR_PREFIXES: Tuple[str, ...] = (
        "title", "name", "label", "desc", "description", "text",
        "message", "msg", "greeting", "dialogue", "prompt",
        "tooltip", "hint", "quest", "objective", "chapter",
        "status", "note", "about", "caption", "header",
        "subtitle", "credit", "intro", "outro", "warning",
        "menu", "choice", "option",
    )

    TRANSLATABLE_VAR_SUFFIXES: Tuple[str, ...] = (
        "_title", "_name", "_label", "_desc", "_description",
        "_text", "_message", "_msg", "_greeting", "_dialogue",
        "_prompt", "_tooltip", "_hint", "_quest", "_note",
        "_caption", "_header", "_subtitle", "_menu", "_choice",
        "_option", "_warning", "_about", "_credit",
    )

    TRANSLATABLE_VAR_EXACT: Set[str] = {
        "who", "what", "save_name", "about", "greeting",
        "farewell", "bio", "motto", "slogan",
    }

    NON_TRANSLATABLE_VAR_PREFIXES: Tuple[str, ...] = (
        "persistent.", "style.", "_",
        "audio.", "sound.", "music.", "voice.",
        "image", "layer", "transform", "transition",
        "color", "colour", "font", "size",
    )

    NON_TRANSLATABLE_VAR_SUFFIXES: Tuple[str, ...] = (
        "_path", "_file", "_dir", "_url", "_image", "_img",
        "_icon", "_sound", "_sfx", "_music", "_voice",
        "_audio", "_font", "_style", "_color", "_alpha",
        "_size", "_pos", "_xpos", "_ypos", "_delay",
        "_speed", "_volume", "_channel", "_layer",
        "_tag", "_id", "_key", "_type", "_class",
    )

    NON_TRANSLATABLE_VAR_EXACT: Set[str] = {
        "version", "save_directory", "window_icon",
        "developer", "log", "searchpath",
    }

    # -------------------------------------------------------------------------
    # Technical string patterns (false positive prevention)
    # -------------------------------------------------------------------------
    TECHNICAL_STRING_PATTERNS: Tuple[str, ...] = (
        r'(?i).*\.(rpy|rpyc|rpymc|rpym|png|jpg|jpeg|webp|gif|bmp|svg'
        r'|ogg|mp3|wav|flac|opus|mp4|webm|avi|mkv'
        r'|ttf|otf|woff|woff2|json|txt|csv|xml|ini|cfg)$',
        r'^(screens?|master|transient|overlay|top|bottom)$',
        r'^[a-z_]+\.[a-z_]+\.[a-z_]+$',    # three.dot.qualified.names
        r'^#[0-9a-fA-F]{3,8}$',             # color hex codes
        r'^\d+(\.\d+)?$',                    # pure numbers
        r'^.$',                               # single character
        r'^\s*$',                             # whitespace only
        r'^\[[\w.]+\]$',                     # [placeholder] only
        r'^\{[\w.]+\}$',                     # {placeholder} only
        r'^[a-z][a-zA-Z0-9]*$',             # camelCase identifiers
        r'^[a-z_][a-z0-9_]*$',              # snake_case identifiers
        r'^https?://.*$',                     # URLs
        r'^[A-Z][A-Z0-9_]+$',               # CONSTANT_NAMES
    )

    # Minimum static text ratio for f-string extraction
    FSTRING_MIN_STATIC_RATIO: float = 0.30

    # Minimum string length for bare define/default extraction
    MIN_BARE_STRING_LENGTH: int = 2


# =============================================================================
# VARIABLE NAME ANALYZER
# =============================================================================

class DeepVariableAnalyzer:
    """Heuristic analyzer for variable names to determine translatability."""

    def __init__(self, config: DeepExtractionConfig = None):
        self.config = config or DeepExtractionConfig()
        self._tech_patterns = [
            re.compile(p)
            for p in self.config.TECHNICAL_STRING_PATTERNS
        ]

    def score_var_name(self, var_name: str) -> float:
        """
        Score a variable name's likelihood of carrying translatable text.

        Returns:
            0.0..1.0 where higher = more likely translatable
        """
        if not var_name:
            return 0.5

        # v2.7.2: Pre-check case before lowercasing
        is_all_upper = var_name.isupper()
        
        score = 0.5
        name_lower = var_name.lower()

        # Strip store prefix for analysis
        base_name = name_lower
        for prefix in ("store.", "default.", "define."):
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]

        # Extract final component (after last dot)
        parts = base_name.rsplit(".", 1)
        leaf = parts[-1] if parts else base_name
        namespace = parts[0] if len(parts) > 1 else ""

        # --- Exact matches ---
        if leaf in self.config.TRANSLATABLE_VAR_EXACT:
            return 0.90
        if leaf in self.config.NON_TRANSLATABLE_VAR_EXACT:
            return 0.05

        # --- Config text vars (special whitelist) ---
        if name_lower in self.config.CONFIG_TEXT_VARS:
            return 0.90
        if name_lower in self.config.CONFIG_SKIP_VARS:
            return 0.05

        # --- Prefix checks ---
        for prefix in self.config.TRANSLATABLE_VAR_PREFIXES:
            if leaf.startswith(prefix):
                score += 0.25
                break

        for prefix in self.config.NON_TRANSLATABLE_VAR_PREFIXES:
            if name_lower.startswith(prefix):
                score -= 0.35
                break

        # --- Suffix checks ---
        for suffix in self.config.TRANSLATABLE_VAR_SUFFIXES:
            if leaf.endswith(suffix):
                score += 0.25
                break

        for suffix in self.config.NON_TRANSLATABLE_VAR_SUFFIXES:
            if leaf.endswith(suffix):
                score -= 0.35
                break

        # --- Namespace penalties ---
        if namespace in ("persistent", "config", "style", "gui"):
            # config and gui can have text, but default to cautious
            if namespace in ("persistent", "style"):
                score -= 0.3

        # --- Uppercase Constant Refinement (v2.7.2) ---
        # If it's all uppercase, it's a constant.
        # Constants are often internal IDs/enums - we start them with a slightly lower bias.
        if is_all_upper and len(var_name) > 2:
            # Shift baseline if not already boosted by prefix/suffix
            if score == 0.5:
                score = 0.45 
            
            # If it passes technical namespace check, give it a small nudge back
            # but usually it needs a translatable suffix (_TITLE, _NAME) to pass.
            if namespace not in ("config", "gui", "style", "persistent"):
                 # Small nudge if it's long - likely a sentence or name
                 if len(var_name) > 10:
                     score += 0.1 

        # Clamp
        return max(0.0, min(1.0, score))

    def is_likely_translatable(self, var_name: str, threshold: float = 0.50) -> bool:
        """Quick check: is var_name likely to hold translatable text?"""
        return self.score_var_name(var_name) >= threshold

    def classify(self, var_name: str) -> str:
        """
        Classify a variable name.

        Returns: "translatable" | "non_translatable" | "uncertain"
        """
        score = self.score_var_name(var_name)
        if score >= 0.70:
            return "translatable"
        elif score < 0.30:
            return "non_translatable"
        return "uncertain"

    def is_technical_string(self, text: str) -> bool:
        """Check if a string matches known technical patterns."""
        if not text or len(text.strip()) < 2:
            return True
        for pat in self._tech_patterns:
            if pat.fullmatch(text.strip()):
                return True
        return False


def confidence_band(score: float) -> str:
    """Map a numeric extraction score to a coarse confidence band."""
    if score >= 0.85:
        return "confirmed"
    if score >= 0.60:
        return "probable"
    return "candidate"


def resolve_minimum_extraction_confidence(config_manager=None, default: float = 0.0) -> float:
    """Safely read the configured extraction threshold.

    MagicMock values should fall back to `default` instead of being coerced
    into an arbitrary numeric value.
    """
    if config_manager is None:
        return default

    ts = getattr(config_manager, "translation_settings", None)
    if ts is None:
        ts = config_manager

    raw = getattr(ts, "minimum_extraction_confidence", default)
    if isinstance(raw, (int, float)):
        return max(0.0, min(1.0, float(raw)))
    if isinstance(raw, str):
        try:
            return max(0.0, min(1.0, float(raw.strip())))
        except (TypeError, ValueError):
            return default
    return default


def score_extraction_confidence(
    text: str,
    text_type: str = "",
    context: str = "",
    context_path: Optional[List[str]] = None,
    character: str = "",
    var_name: str = "",
) -> float:
    """Score how safe a candidate is to treat as user-facing text.

    The score is intentionally conservative. Stable dialogue/UI patterns get
    a high score, while generic strings, technical identifiers, and code-like
    fragments get downweighted.
    """
    text = (text or "").strip()
    if not text:
        return 0.0

    analyzer = _shared_analyzer
    if analyzer.is_technical_string(text):
        return 0.0

    lowered_text = text.lower()
    lowered_context = (context or "").lower()
    lowered_path = " / ".join((p or "" for p in (context_path or []))).lower()
    combined_context = f"{lowered_context} {lowered_path} {character or ''} {var_name or ''}".lower()

    base_scores = {
        "translatable_string": 0.99,
        "immediate_translation": 0.99,
        "python_translatable": 0.99,
        "dialogue": 0.94,
        "narration": 0.94,
        "nvl_dialogue": 0.92,
        "monologue": 0.92,
        "menu": 0.90,
        "menu_choice": 0.90,
        "ui_action": 0.92,
        "notify": 0.93,
        "confirm": 0.93,
        "input": 0.91,
        "screen_text": 0.82,
        "screen": 0.82,
        "textbutton": 0.84,
        "imagebutton": 0.82,
        "label": 0.80,
        "text_displayable": 0.84,
        "show_text": 0.82,
        "ui": 0.80,
        "button": 0.78,
        "character_name": 0.70,
        "define_text": 0.68,
        "config_text": 0.66,
        "string": 0.55,
        "data_string": 0.45,
        "python_ast": 0.50,
        "call_arg": 0.52,
        "python_list": 0.48,
        "python_dict": 0.48,
        "list_item": 0.55,
    }
    score = base_scores.get((text_type or "").lower(), 0.58)

    if any(token in combined_context for token in ("python/_", "python/__", "python/___", "translate:", "translate_string")):
        score += 0.20
    if any(token in combined_context for token in ("define ", "default ")):
        score += 0.12
    if any(token in combined_context for token in ("say", "menu", "confirm", "notify", "tooltip", "display_menu", "textbutton", "text_displayable")):
        score += 0.10
    if any(token in combined_context for token in ("screen:", "screen ", "screen_")):
        score += 0.08
    if any(token in combined_context for token in ("action", "caption", "title", "prompt")):
        score += 0.06

    if var_name:
        score = (score * 0.72) + (_shared_analyzer.score_var_name(var_name) * 0.28)

    if character and character.strip():
        score += 0.03

    words = [part for part in re.split(r"\s+", text) if part]
    alpha_words = [part for part in words if any(ch.isalpha() for ch in part)]
    if len(alpha_words) >= 2:
        score += 0.04
    elif len(alpha_words) == 1 and len(text) > 12:
        score += 0.02
    if (text_type or "").lower() in {"string", "data_string", "define_text", "config_text"}:
        if len(alpha_words) >= 2 and any(word[:1].isupper() for word in alpha_words):
            score += 0.05

    # Gentle penalties for code-like / identifier-like strings.
    if re.search(r'^(?:https?://|ftp://|mailto:|file://|www\.)', lowered_text):
        score -= 0.45
    if re.search(r'^[#\d]', text):
        score -= 0.15
    if re.search(r'^[A-Za-z_][A-Za-z0-9_]*$', text) and " " not in text:
        score -= 0.18
    if re.search(r'^[A-Z][A-Z0-9_]+$', text):
        score -= 0.12
    if "/" in text and " " not in text:
        score -= 0.20
    if "=" in text and len(text) < 60:
        score -= 0.10
    if "{" in text or "[" in text:
        # Preserve tagged dialogue, but do not over-trust it unless other cues exist.
        score -= 0.03

    return max(0.0, min(1.0, score))


# Module-level shared analyzer instance (avoids re-compiling 15 regex patterns per call)
_shared_analyzer = DeepVariableAnalyzer()


# =============================================================================
# F-STRING TEMPLATE RECONSTRUCTOR
# =============================================================================

class FStringReconstructor:
    """
    Reconstructs f-string templates for parser-side extraction.

    Converts f"Welcome {name}, you have {count} items"
    into    "Welcome [name], you have [count] items"

    Mirrors the RPYC reader's visit_JoinedStr but works on raw source text.
    """

    # Regex to match f-string expressions: {expr}, {expr!r}, {expr:format}
    _FSTRING_EXPR_RE = re.compile(
        r'\{('
        r'[^{}]*'          # simple expressions
        r'(?:\{[^{}]*\})*' # nested braces (one level)
        r'[^{}]*'
        r')\}'
    )

    @classmethod
    def extract_template(cls, fstring_content: str) -> Optional[str]:
        """
        Extract a translatable template from f-string content.

        Args:
            fstring_content: The content inside the f-string quotes (without f prefix and quotes)

        Returns:
            Template string with {expr} → [expr], or None if not meaningful.
        """
        if not fstring_content:
            return None

        # Replace {expressions} with [expressions] for Ren'Py compatibility
        template = cls._FSTRING_EXPR_RE.sub(r'[\1]', fstring_content)

        # Calculate static text ratio
        total_len = len(fstring_content)
        if total_len == 0:
            return None

        # Count placeholder overhead: only the bracket pairs count as "dynamic",
        # not the variable names themselves (which are part of the translated template).
        # Each [expr] contributes 2 chars of overhead (the brackets).
        placeholder_count = len(re.findall(r'\[[^\]]+\]', template))
        placeholder_overhead = placeholder_count * 2  # just the [ and ] chars
        static_len = total_len - placeholder_overhead
        static_ratio = static_len / total_len if total_len > 0 else 0

        if static_ratio < DeepExtractionConfig.FSTRING_MIN_STATIC_RATIO:
            return None

        # Must have at least some alphabetic chars in static part
        static_text = re.sub(r'\[[^\]]+\]', '', template)
        if not any(ch.isalpha() for ch in static_text):
            return None

        return template

    @classmethod
    def extract_from_ast_node(cls, node: ast.JoinedStr, source_code: str = "") -> Optional[str]:
        """
        Extract template from an AST JoinedStr node.
        Used by both parser AST scan and RPYC reader.
        """
        parts = []
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                parts.append(val.value)
            elif isinstance(val, ast.FormattedValue):
                try:
                    seg = ast.get_source_segment(source_code, val.value)
                    if seg:
                        parts.append(f"[{seg}]")
                    else:
                        # Source segment unavailable — skip this f-string entirely
                        # rather than inserting a fake [_expr_] placeholder that
                        # would cause a Ren'Py NameError at runtime.
                        return None
                except Exception:
                    return None

        full_str = "".join(parts)
        if len(full_str) <= 2 or full_str.startswith("["):
            return None
        return full_str


# =============================================================================
# MULTI-LINE STRUCTURE PARSER
# =============================================================================

class MultiLineStructureParser:
    """
    Parses multi-line dict/list structures in define/default statements.

    Example:
        define quest_data = {
            "title": "Dragon Slayer",
            "desc": "Kill the mighty dragon",
        }
    """

    # Import DATA_KEY_WHITELIST at usage time to avoid circular import
    _MULTILINE_START_RE = re.compile(
        r'^\s*(?:define\s+(?:-?\d+\s+)?|default\s+)'
        r'(?P<var_name>[\w.]+)\s*=\s*(?P<start_char>[\{\[]).*$'
    )

    @staticmethod
    def _count_brackets_in_line(line: str, open_char: str, close_char: str) -> int:
        """
        Count net bracket depth change in a line, aware of strings and escapes.
        
        Handles:
        - Escape sequences (\\)
        - Single/double quoted strings
        - Triple-quoted strings (''' and \"\"\")
        
        Returns:
            Net bracket depth change (positive = more opens, negative = more closes)
        """
        count = 0
        in_string = False
        string_char = None       # ' or "
        triple_quote = False     # Whether current string uses triple quotes
        escaped = False
        i = 0
        length = len(line)
        
        while i < length:
            ch = line[i]
            
            if escaped:
                escaped = False
                i += 1
                continue
            
            if ch == '\\':
                escaped = True
                i += 1
                continue
            
            if in_string:
                if triple_quote:
                    # Triple-quote: look for three consecutive matching chars
                    if ch == string_char and i + 2 < length and line[i+1] == string_char and line[i+2] == string_char:
                        in_string = False
                        triple_quote = False
                        i += 3
                        continue
                else:
                    # Single-quote string: close on matching char
                    if ch == string_char:
                        in_string = False
                i += 1
                continue
            
            # Not in string — check for string start
            if ch in ('"', "'"):
                # Check for triple quote
                if i + 2 < length and line[i+1] == ch and line[i+2] == ch:
                    in_string = True
                    string_char = ch
                    triple_quote = True
                    i += 3
                    continue
                else:
                    in_string = True
                    string_char = ch
                    i += 1
                    continue
            
            if ch == open_char:
                count += 1
            elif ch == close_char:
                count -= 1
            
            i += 1
        
        return count

    @classmethod
    def detect_multiline_start(cls, line: str) -> Optional[Dict[str, Any]]:
        """
        Detect a define/default that opens a multi-line structure.

        Returns:
            {"var_name": str, "start_char": "{" or "[", "indent": int}
            or None if not a multi-line structure start.
        """
        m = cls._MULTILINE_START_RE.match(line)
        if not m:
            return None

        start_char = m.group("start_char")
        close_char = "}" if start_char == "{" else "]"

        # Check if the structure closes on the same line
        # Uses triple-quote-aware string tracking
        count = cls._count_brackets_in_line(line, start_char, close_char)

        if count <= 0:
            # Closes on same line — not truly multi-line
            return None

        return {
            "var_name": m.group("var_name"),
            "start_char": start_char,
            "indent": len(line) - len(line.lstrip()),
        }

    @classmethod
    def collect_block(cls, lines: List[str], start_idx: int, info: Dict[str, Any]) -> Tuple[str, int]:
        """
        Collect lines from start_idx until brackets are balanced.

        Returns:
            (collected_code, end_idx)
        """
        start_char = info["start_char"]
        close_char = "}" if start_char == "{" else "]"
        depth = 0
        collected = []
        end_idx = start_idx

        for i in range(start_idx, len(lines)):
            line = lines[i]
            # Count brackets outside strings (triple-quote-aware)
            depth += cls._count_brackets_in_line(line, start_char, close_char)

            collected.append(line)
            end_idx = i

            if depth <= 0:
                break

        return "\n".join(collected), end_idx

    @classmethod
    def extract_translatable_values(
        cls,
        var_name: str,
        code: str,
        whitelist: Set[str] = None,
        blacklist: Set[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parse collected code with AST and extract translatable string values.

        Only extracts values whose dict keys are in the whitelist.
        For lists, extracts all string elements if the var_name is translatable-looking.
        """
        from .parser import DATA_KEY_WHITELIST, DATA_KEY_BLACKLIST

        if whitelist is None:
            whitelist = DATA_KEY_WHITELIST
        if blacklist is None:
            blacklist = DATA_KEY_BLACKLIST

        results: List[Dict[str, Any]] = []
        analyzer = _shared_analyzer

        # Try to extract the value expression from the full define/default line
        # Strip: define var_name = <expression>
        assign_re = re.compile(
            r'^\s*(?:define\s+(?:-?\d+\s+)?|default\s+)'
            r'[\w.]+\s*=\s*', re.MULTILINE
        )
        m = assign_re.match(code)
        expr_code = code[m.end():] if m else code

        try:
            tree = ast.parse(expr_code, mode='eval')
        except SyntaxError:
            try:
                tree = ast.parse(expr_code, mode='exec')
            except SyntaxError:
                return results

        body = tree.body if hasattr(tree, 'body') and not isinstance(tree.body, list) else tree

        def visit_value(node: ast.AST, key_ctx: Optional[str] = None):
            """Recursively visit AST nodes and extract strings."""
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                if len(text) >= DeepExtractionConfig.MIN_BARE_STRING_LENGTH:
                    if not analyzer.is_technical_string(text):
                        results.append({
                            "text": text,
                            "context": key_ctx or var_name,
                            "lineno": getattr(node, "lineno", 0),
                        })

            elif isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    k_str = None
                    if k and isinstance(k, ast.Constant) and isinstance(k.value, str):
                        k_str = k.value.lower()

                    if k_str:
                        if k_str in blacklist:
                            continue  # Skip blacklisted keys
                        if k_str in whitelist:
                            visit_value(v, key_ctx=k_str)
                        # For unknown keys, still recurse into nested structures
                        elif isinstance(v, (ast.Dict, ast.List)):
                            visit_value(v, key_ctx=k_str)
                    else:
                        visit_value(v, key_ctx=key_ctx)

            elif isinstance(node, ast.List):
                for elt in node.elts:
                    visit_value(elt, key_ctx=key_ctx)

            elif isinstance(node, ast.Tuple):
                for elt in node.elts:
                    visit_value(elt, key_ctx=key_ctx)

            elif isinstance(node, ast.JoinedStr):
                template = FStringReconstructor.extract_from_ast_node(node, expr_code)
                if template:
                    results.append({
                        "text": template,
                        "context": key_ctx or var_name,
                        "lineno": getattr(node, "lineno", 0),
                        "is_fstring": True,
                    })

        # Visit the expression body
        if isinstance(body, ast.Expression):
            visit_value(body.body)
        elif isinstance(body, ast.Module):
            for stmt in body.body:
                if isinstance(stmt, ast.Expr):
                    visit_value(stmt.value)
                elif isinstance(stmt, ast.Assign):
                    visit_value(stmt.value)
        else:
            visit_value(body)

        return results
