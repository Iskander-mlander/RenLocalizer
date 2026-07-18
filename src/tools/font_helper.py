# -*- coding: utf-8 -*-
"""
RenLocalizer Font Helper Module
===============================

Tool for checking font compatibility with target languages.
Helps prevent the common issue of missing glyphs (□□□) when displaying
translated text in fonts that don't support the target language's characters.

Features:
1. Check if a font supports required characters
2. Suggest alternative fonts
3. Generate sample text for visual testing
4. Report missing character ranges
"""

import os
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any

# Try to import fontTools (optional dependency)
try:
    from fontTools.ttLib import TTFont
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False


@dataclass
class FontCheckResult:
    """Result of checking font compatibility."""
    font_path: str
    language: str
    supported: bool
    coverage_percent: float
    missing_chars: List[str] = field(default_factory=list)
    sample_text: str = ""
    
    def __str__(self) -> str:
        status = "✅ SUPPORTED" if self.supported else "❌ MISSING GLYPHS"
        return (
            f"Font: {os.path.basename(self.font_path)}\n"
            f"Language: {self.language}\n"
            f"Status: {status}\n"
            f"Coverage: {self.coverage_percent:.1f}%\n"
            f"Missing: {len(self.missing_chars)} characters"
        )


@dataclass
class FontRiskFinding:
    """Static analysis result for custom/hardcoded font usage."""
    category: str
    label: str
    file_path: str
    line_number: int
    line_preview: str


# Character sets for different languages
LANGUAGE_CHAR_SETS: Dict[str, Tuple[str, str]] = {
    # (essential_chars, sample_text)
    "tr": (
        "ÇçĞğİıÖöŞşÜü",
        "Merhaba! Günaydın. İyi akşamlar. Çok güzel. Şöyle böyle."
    ),
    "ru": (
        "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "Привет! Как дела? Спасибо, хорошо."
    ),
    "uk": (
        "ҐґЄєІіЇї" + "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгдежзийклмнопрстуфхцчшщьюя",
        "Привіт! Як справи? Дякую, добре."
    ),
    "ja": (
        "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん",
        "こんにちは！元気ですか？ありがとうございます。"
    ),
    "ko": (
        "가나다라마바사아자차카타파하",
        "안녕하세요! 잘 지내세요? 감사합니다."
    ),
    "zh": (
        "的一是不了在人有我他这个们中来上大为和国地到以说时要就出会可也你对生能而子那得于着下自之年过发后作里",
        "你好！你好吗？谢谢你。"
    ),
    "zh_tw": (
        "的一是不了在人有我他這個們中來上大為和國地到以說時要就出會可也你對生能而子那得於著下自之年過發後作裡",
        "你好！你好嗎？謝謝你。"
    ),
    "ar": (
        "ابتثجحخدذرزسشصضطظعغفقكلمنهوي",
        "مرحبا! كيف حالك؟ شكرا لك."
    ),
    "he": (
        "אבגדהוזחטיכלמנסעפצקרשת",
        "שלום! מה שלומך? תודה רבה."
    ),
    "th": (
        "กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ",
        "สวัสดี! คุณสบายดีไหม? ขอบคุณครับ"
    ),
    "vi": (
        "ĂăÂâĐđÊêÔôƠơƯưÀàẢảÃãÁáẠạẦầẨẩẪẫẤấẬậ",
        "Xin chào! Bạn khỏe không? Cảm ơn bạn."
    ),
    "pl": (
        "ĄąĆćĘęŁłŃńÓóŚśŹźŻż",
        "Cześć! Jak się masz? Dziękuję."
    ),
    "cs": (
        "ÁáČčĎďÉéĚěÍíŇňÓóŘřŠšŤťÚúŮůÝýŽž",
        "Ahoj! Jak se máš? Děkuji."
    ),
    "hu": (
        "ÁáÉéÍíÓóÖöŐőÚúÜüŰű",
        "Szia! Hogy vagy? Köszönöm."
    ),
    "ro": (
        "ĂăÂâÎîȘșȚț",
        "Bună! Ce mai faci? Mulțumesc."
    ),
    "el": (
        "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψω",
        "Γεια σου! Πώς είσαι; Ευχαριστώ."
    ),
    "de": (
        "ÄäÖöÜüß",
        "Hallo! Wie geht es dir? Danke schön."
    ),
    "fr": (
        "ÀàÂâÆæÇçÉéÈèÊêËëÎîÏïÔôŒœÙùÛûÜüŸÿ",
        "Bonjour! Comment ça va? Merci beaucoup."
    ),
    "es": (
        "ÁáÉéÍíÑñÓóÚúÜü¿¡",
        "¡Hola! ¿Cómo estás? Muchas gracias."
    ),
    "pt": (
        "ÀàÁáÂâÃãÇçÉéÊêÍíÓóÔôÕõÚú",
        "Olá! Como você está? Muito obrigado."
    ),
    "it": (
        "ÀàÈèÉéÌìÍíÎîÒòÓóÙùÚú",
        "Ciao! Come stai? Grazie mille."
    ),
}


FONT_RISK_PATTERNS: Dict[str, re.Pattern[str]] = {
    "text_font_arg": re.compile(r"\bText\s*\([^\n#]*\bfont\s*=", re.IGNORECASE),
    "what_font": re.compile(r"\bwhat_font\s*=", re.IGNORECASE),
    "who_font": re.compile(r"\bwho_font\s*=", re.IGNORECASE),
    "style_font": re.compile(r"\bstyle\s+\w+[^\n#]*\bfont\b", re.IGNORECASE),
    "font_tag": re.compile(r"\{font=[^}]+\}", re.IGNORECASE),
    "font_group": re.compile(r"\bFontGroup\s*\(", re.IGNORECASE),
    "font_name_map": re.compile(r"\bconfig\.font_name_map\b", re.IGNORECASE),
    "font_replacement_map": re.compile(r"\bconfig\.font_replacement_map\b", re.IGNORECASE),
    "image_font": re.compile(r"\brenpy\.register_(?:bmfont|mudgefont|sfont)\b", re.IGNORECASE),
}

RISK_LABELS: Dict[str, str] = {
    "text_font_arg": "Text(..., font=...)",
    "what_font": "what_font=",
    "who_font": "who_font=",
    "style_font": "style ... font",
    "font_tag": "{font=...}",
    "font_group": "FontGroup()",
    "font_name_map": "config.font_name_map",
    "font_replacement_map": "config.font_replacement_map",
    "image_font": "image-based font registration",
}


class FontHelper:
    """
    Helper for checking font compatibility with different languages.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not FONTTOOLS_AVAILABLE:
            self.logger.warning(
                "fontTools not available. Install with: pip install fonttools\n"
                "Font checking will be limited."
            )
    
    def check_font(self, font_path: str, language: str) -> FontCheckResult:
        """
        Check if a font supports a specific language.
        
        Args:
            font_path: Path to TTF/OTF font file
            language: Language code (e.g., 'tr', 'ru', 'ja')
        
        Returns:
            FontCheckResult with coverage information
        """
        # Get character set for language
        if language not in LANGUAGE_CHAR_SETS:
            return FontCheckResult(
                font_path=font_path,
                language=language,
                supported=False,
                coverage_percent=0.0,
                missing_chars=[],
                sample_text=f"Unknown language: {language}"
            )
        
        essential_chars, sample_text = LANGUAGE_CHAR_SETS[language]
        
        if not FONTTOOLS_AVAILABLE:
            # Cannot check without fontTools
            return FontCheckResult(
                font_path=font_path,
                language=language,
                supported=True,  # Assume supported
                coverage_percent=100.0,
                missing_chars=[],
                sample_text=f"⚠️ fontTools not installed - cannot verify\n\nSample: {sample_text}"
            )
        
        if not os.path.exists(font_path):
            return FontCheckResult(
                font_path=font_path,
                language=language,
                supported=False,
                coverage_percent=0.0,
                missing_chars=list(essential_chars),
                sample_text=f"Font file not found: {font_path}"
            )
        
        try:
            font = TTFont(font_path)
            cmap = font.getBestCmap()
            
            if cmap is None:
                return FontCheckResult(
                    font_path=font_path,
                    language=language,
                    supported=False,
                    coverage_percent=0.0,
                    missing_chars=list(essential_chars),
                    sample_text="Could not read font character map"
                )
            
            # Check which characters are missing
            missing = []
            for char in essential_chars:
                if ord(char) not in cmap:
                    missing.append(char)
            
            # Calculate coverage
            total = len(essential_chars)
            supported_count = total - len(missing)
            coverage = (supported_count / total * 100) if total > 0 else 0
            
            # Determine if font is usable (allow some missing)
            is_supported = coverage >= 90.0
            
            return FontCheckResult(
                font_path=font_path,
                language=language,
                supported=is_supported,
                coverage_percent=coverage,
                missing_chars=missing,
                sample_text=sample_text
            )
            
        except Exception as e:
            self.logger.error(f"Error checking font {font_path}: {e}")
            return FontCheckResult(
                font_path=font_path,
                language=language,
                supported=False,
                coverage_percent=0.0,
                missing_chars=[],
                sample_text=f"Error reading font: {e}"
            )
    
    def find_game_fonts(self, game_dir: str) -> List[str]:
        """
        Find all font files in a game directory.
        
        Args:
            game_dir: Path to game directory
        
        Returns:
            List of font file paths
        """
        fonts = []
        font_extensions = ('.ttf', '.otf', '.ttc', '.woff', '.woff2')
        
        for root, dirs, files in os.walk(game_dir):
            for file in files:
                if file.lower().endswith(font_extensions):
                    fonts.append(os.path.join(root, file))
        
        return fonts
    
    def check_all_fonts(
        self,
        game_dir: str,
        language: str
    ) -> List[FontCheckResult]:
        """
        Check all fonts in a game directory for language compatibility.
        
        Args:
            game_dir: Path to game directory
            language: Target language code
        
        Returns:
            List of FontCheckResult for each font found
        """
        fonts = self.find_game_fonts(game_dir)
        results = []
        
        for font_path in fonts:
            result = self.check_font(font_path, language)
            results.append(result)
        
        return results
    
    def get_sample_text(self, language: str) -> str:
        """Get sample text for a language."""
        if language in LANGUAGE_CHAR_SETS:
            return LANGUAGE_CHAR_SETS[language][1]
        return f"No sample text available for language: {language}"
    
    def get_essential_chars(self, language: str) -> str:
        """Get essential characters for a language."""
        if language in LANGUAGE_CHAR_SETS:
            return LANGUAGE_CHAR_SETS[language][0]
        return ""
    
    def generate_font_test_file(
        self,
        output_path: str,
        language: str,
        font_name: str = "gui.text_font"
    ) -> str:
        """
        Generate a Ren'Py test screen to visually verify font compatibility.
        
        Args:
            output_path: Where to save the test file
            language: Target language
            font_name: Font variable name in Ren'Py
        
        Returns:
            Path to generated file
        """
        if language not in LANGUAGE_CHAR_SETS:
            raise ValueError(f"Unknown language: {language}")
        
        essential, sample = LANGUAGE_CHAR_SETS[language]
        
        content = f"""\
# -*- coding: utf-8 -*-
# Font Compatibility Test Screen
# Generated by RenLocalizer
# Language: {language}

screen font_test():
    tag menu
    
    frame:
        xalign 0.5
        yalign 0.5
        xpadding 50
        ypadding 30
        
        vbox:
            spacing 20
            
            text "Font Compatibility Test" size 40
            text "Language: {language}" size 24
            
            null height 20
            
            text "Essential Characters:" size 20
            text "{essential}" size 28
            
            null height 20
            
            text "Sample Text:" size 20
            text "{sample}" size 28
            
            null height 30
            
            textbutton "Close" action Return() xalign 0.5


label font_test_label:
    call screen font_test
    return
"""
        
        with open(output_path, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write(content)
        
        return output_path
    
    def suggest_fonts(self, language: str) -> List[str]:
        """
        Suggest commonly used fonts that support a language.
        
        Args:
            language: Target language code
        
        Returns:
            List of suggested font names
        """
        # Common fonts known to have good language support
        FONT_SUGGESTIONS = {
            "ja": [
                "Noto Sans JP",
                "M PLUS 1p",
                "Kosugi Maru",
                "Sawarabi Gothic",
                "Source Han Sans JP",
            ],
            "ko": [
                "Noto Sans KR",
                "Nanum Gothic",
                "Malgun Gothic",
                "Source Han Sans KR",
            ],
            "zh": [
                "Noto Sans SC",
                "Source Han Sans SC",
                "Microsoft YaHei",
                "PingFang SC",
            ],
            "zh_tw": [
                "Noto Sans TC",
                "Source Han Sans TC",
                "Microsoft JhengHei",
                "PingFang TC",
            ],
            "ru": [
                "Roboto",
                "Open Sans",
                "Noto Sans",
                "PT Sans",
                "Ubuntu",
            ],
            "ar": [
                "Noto Sans Arabic",
                "Amiri",
                "Cairo",
                "Tajawal",
            ],
            "he": [
                "Noto Sans Hebrew",
                "Open Sans Hebrew",
                "Rubik",
                "Heebo",
            ],
            "th": [
                "Noto Sans Thai",
                "Sarabun",
                "Prompt",
                "Kanit",
            ],
            "tr": [
                "Roboto",
                "Open Sans",
                "Noto Sans",
                "Inter",
                "Poppins",
            ],
        }
        
        # Default Latin fonts work for most European languages
        default_fonts = [
            "Roboto",
            "Open Sans",
            "Noto Sans",
            "Inter",
            "Lato",
            "Source Sans Pro",
        ]
        
        return FONT_SUGGESTIONS.get(language, default_fonts)

    def analyze_font_risks(self, game_dir: str) -> Dict[str, Any]:
        """Scan project scripts for hardcoded/custom font usage.

        This helps estimate whether the automatic font fixer may only provide
        partial coverage on a project.
        """
        root = Path(game_dir)
        if (root / "game").exists():
            root = root / "game"

        findings: List[FontRiskFinding] = []
        counts = {key: 0 for key in FONT_RISK_PATTERNS}

        for path in root.rglob("*.rpy"):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                try:
                    lines = path.read_text(encoding="latin-1").splitlines()
                except Exception:
                    continue
            except Exception:
                continue

            for line_number, line in enumerate(lines, 1):
                for category, pattern in FONT_RISK_PATTERNS.items():
                    if not pattern.search(line):
                        continue
                    counts[category] += 1
                    findings.append(
                        FontRiskFinding(
                            category=category,
                            label=RISK_LABELS[category],
                            file_path=str(path),
                            line_number=line_number,
                            line_preview=line.strip()[:220],
                        )
                    )

        findings.sort(key=lambda item: (item.category, item.file_path, item.line_number))
        return {
            "total_findings": len(findings),
            "counts": counts,
            "findings": findings,
        }


def check_font_for_project(
    game_dir: str,
    target_language: str,
    verbose: bool = False
) -> Dict[str, any]:
    """
    Convenience function to check all fonts in a project.
    
    Args:
        game_dir: Path to game directory
        target_language: Target language code
        verbose: Print detailed output
    
    Returns:
        Summary dict with results
    """
    helper = FontHelper()
    results = helper.check_all_fonts(game_dir, target_language)
    risk_report = helper.analyze_font_risks(game_dir)
    
    summary = {
        'fonts_checked': len(results),
        'compatible_fonts': sum(1 for r in results if r.supported),
        'incompatible_fonts': sum(1 for r in results if not r.supported),
        'results': results,
        'suggestions': helper.suggest_fonts(target_language),
        'risk_report': risk_report,
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Font Compatibility Check for {target_language.upper()}")
        print(f"{'='*60}\n")
        
        for result in results:
            print(result)
            if result.missing_chars:
                print(f"  Missing: {''.join(result.missing_chars[:20])}{'...' if len(result.missing_chars) > 20 else ''}")
            print()
        
        print(f"\nSuggested fonts for {target_language}:")
        for font in summary['suggestions']:
            print(f"  - {font}")

        print(f"\nFont override risk findings: {risk_report['total_findings']}")
    
    return summary
