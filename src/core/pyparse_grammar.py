"""
Lightweight, SDK-free Ren'Py grammar built around a state machine and indentation.

Goals:
- No Ren'Py SDK dependency
- Robust triple-quote handling (paragraph split)
- Menu/screen/python/_() coverage with placeholder preservation
- Logical line joining (line continuation with backslash)
"""
from typing import List, Dict


def extract_with_pyparsing(content: str, file_path: str = "") -> List[Dict]:
    """
    "Pyparsing" adı kalsa da, burada indentation tabanlı bir state machine var.
    Ren'Py SDK yüklenmeden diyalog/menü/screen/_() metinlerini çıkarır.
    """
    try:  # Optional perf boost if pyparsing yüklü
        from pyparsing import ParserElement

        ParserElement.setDefaultWhitespaceChars(" \t")
        ParserElement.enablePackrat()
    except Exception:
        pass

    import re

    entries: List[Dict] = []

    # v2.5.0: "default " removed from TECHNICAL_PREFIXES
    # because default dict/list literals may contain translatable strings
    # e.g., default quest = {"anna": ["Start by helping her..."]}
    TECHNICAL_PREFIXES = (
        "image ",
        "define ",
        # "default ",  # Removed - needs special handling for dict/list content
        # "transform ", # Removed v2.6.4 to allow scanning text inside ATL transforms
        "style ",
        "config.",
        "gui.",
        "store.",
        "layout.",
        "label hide",
        # Screen property statements — bunlar asla diyalog değil; dialog_re backtracking önlenir
        "action ",
        "focus_mask ",
        "modal ",
        "imagebutton",
        "imagebutton:",
        "add ",
        "at ",
        "zorder ",
        "xalign ",
        "yalign ",
        "xpos ",
        "ypos ",
        "spacing ",
        "padding ",
        "background ",
        "foreground ",
        "hovered ",
        "unhovered ",
        "selected_",
        "insensitive_",
        "activate_sound ",
        "hover_sound ",
        "mouse ",
        "keysym ",
        "sensitive ",
        "visible ",
        "pos ",
        "size ",
        "rotate ",
        "zoom ",
        "crop ",
        "xysize ",
    )

    dialog_re = re.compile(
        r'^(?P<char>[A-Za-z_][\w\.]*)\s+(?P<quote>(?:[fFuUrR][fFuUrR]?)?(?:"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\'))'
    )
    narrator_re = re.compile(r'^(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')')
    menu_choice_re = re.compile(
        r'^\s*(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')\s*(?:if\s+[^:]+)?\s*:\s*$'
    )
    screen_elem_re = re.compile(
        r'\b(text|label|tooltip|textbutton)\s+(?:_\s*\(\s*)?(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')(?:\s*\))?'
    )
    python_call_re = re.compile(
        r'(?:__|_)\s*\(\s*(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')\s*\)'
    )
    notify_call_re = re.compile(
        r'renpy\.(?:say|notify)\s*\(\s*(?:[A-Za-z_]\w*\s*,\s*)?(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')'
    )
    text_displayable_re = re.compile(
        r'\bText\s*\(\s*(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')'
    )
    input_call_re = re.compile(
        r'renpy\.input\s*\(\s*(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')'
    )
    triple_start_re = re.compile(
        r'^(?P<prefix>(?:[A-Za-z_]\w*\s+)?)(?P<delim>"""|\'\'\')(?P<body>.*)$'
    )

    # Broader say-statement support: quoted speaker names and image-attribute variants.
    dialogue_speaker_re = (
        r'(?!(?:textbutton|text|label|tooltip|screen|menu|scene|show|hide|call|jump|'
        r'python|init|define|default|style|image|caption|frame|transform)\b)'
        r'[A-Za-z_][\w\.]*'
    )
    dialogue_attr_token = (
        r'(?:@\s*)?-?(?!(?:at|as|behind|onlayer|with|zorder|show|hide|scene|call|jump|'
        r'return|play|stop|queue|pause|python|screen|menu|textbutton|text|label|tooltip|'
        r'window|frame|transform|define|default|style|image|caption)\b)[A-Za-z_][\w-]*'
    )
    dialogue_attr_tail = rf'(?:\s+{dialogue_attr_token})*'
    dialogue_speaker_or_quoted = rf'(?:{dialogue_speaker_re}|"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')'

    dialog_re = re.compile(
        rf'^(?P<char>{dialogue_speaker_or_quoted}){dialogue_attr_tail}\s+(?P<quote>(?:[fFuUrR][fFuUrR]?)?(?:"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\'))'
    )
    triple_start_re = re.compile(
        rf'^(?P<prefix>{dialogue_speaker_or_quoted}{dialogue_attr_tail}\s+)?(?P<delim>"""|\'\'\')(?P<body>.*)$'
    )

    # Regex'leri döngü dışında bir kez derle — protect_placeholders her entry için çağrılıyor
    _nested_var_pat = re.compile(r'\[{2,}[^\]]+\]{2,}')
    _var_pat = re.compile(r"\[[^\[\]]+\]")
    _tag_pat = re.compile(r"\{[^{}]+\}")
    _renpy_tag_pat = re.compile(r'\{/?[a-z]+(?:=[^}]*)?\}')
    # default/data string literal extraction — döngü içinde her satır için derlenmiyecek
    _default_strings_re = re.compile(r'(?<!\\)(?:[fFuUrR][fFuUrR]?)?(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')')

    def protect_placeholders(text: str):
        # NEW v2.4.1: Nested interpolation protection (e.g. [[var]])
        nested_var_pat = _nested_var_pat
        var_pat = _var_pat
        tag_pat = _tag_pat
        # NEW v2.4.1: Ren'Py text tags with values (e.g. {size=30}, {b})
        renpy_tag_pat = _renpy_tag_pat
        
        placeholders = {}
        counter = 0

        def repl(m):
            nonlocal counter
            key = f"__PH_{counter}__"
            placeholders[key] = m.group(0)
            counter += 1
            return key

        # Apply in order: nested first, then regular
        protected = nested_var_pat.sub(repl, text)
        protected = var_pat.sub(repl, protected)
        protected = tag_pat.sub(repl, protected)
        protected = renpy_tag_pat.sub(repl, protected)
        
        return protected, placeholders

    def restore_placeholders(text: str, placeholders: Dict[str, str]):
        for k, v in placeholders.items():
            text = text.replace(k, v)
        return text

    def strip_markup_structurally(text: str) -> str:
        """Remove Ren'Py markup tags and placeholders while keeping visible text."""
        if not text:
            return ""

        output: List[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '\\' and i + 1 < len(text):
                output.append(text[i:i + 2])
                i += 2
                continue

            if ch in ('{', '['):
                close = '}' if ch == '{' else ']'
                depth = 1
                j = i + 1
                in_single = False
                in_double = False
                while j < len(text):
                    c = text[j]
                    if c == '\\' and j + 1 < len(text):
                        j += 2
                        continue
                    if c == "'" and not in_double:
                        in_single = not in_single
                    elif c == '"' and not in_single:
                        in_double = not in_double
                    elif not in_single and not in_double:
                        if ch == '{' and c == '{':
                            depth += 1
                        elif ch == '[' and c == '[':
                            depth += 1
                        elif c == close:
                            depth -= 1
                            if depth == 0:
                                break
                    j += 1

                if depth == 0:
                    i = j + 1
                    continue

            output.append(ch)
            i += 1

        return ''.join(output).strip()

    def normalize_visible_text(text: str) -> str:
        stripped = strip_markup_structurally(text)
        if stripped:
            return stripped
        return re.sub(r'\{/?[^}]*\}|\[[^\]]*\]', '', text or '').strip()

    # Satır devamı (\) ve parantez içi birleştirme
    logical_lines = []
    buffer = ""
    paren_depth = 0
    
    for line in content.splitlines():
        # Strip comments for depth counting purposes only
        clean_line = re.sub(r'#.*$', '', line).strip()
        
        # Count opener/closer balance
        openers = clean_line.count('(') + clean_line.count('[') + clean_line.count('{') 
        closers = clean_line.count(')') + clean_line.count(']') + clean_line.count('}')
        
        # Don't count quoted chars (simple approximation)
        # Detailed quoted string suppression is complex without full lexer, 
        # but basic depth check handles 95% of cases correctly.
        
        if line.rstrip().endswith("\\"):
            buffer += line.rstrip()[:-1] + " "
            continue
            
        # Check if we are inside a data structure
        new_depth = paren_depth + openers - closers
        
        # If we have unbalanced parens or existing buffer, accumulate
        if paren_depth > 0 or buffer:
            buffer += line + "\n" # Keep newline for multi-line strings
            paren_depth = new_depth
            # Safety: eğer buffer 50 satırı aştıysa parantez hiç kapanmıyor demektir
            # (muhtemelen yorum veya string içindeki parantez sayım hatası).
            # Buffer'ı flush et, yoksa tüm dosya tek bir "logical line" olur.
            if paren_depth <= 0 or buffer.count('\n') > 50:
                logical_lines.append(buffer)
                buffer = ""
                paren_depth = 0
            continue
            
        if new_depth > 0:
            buffer = line + "\n"
            paren_depth = new_depth
            continue

        logical_lines.append(line)
        
    if buffer:
        logical_lines.append(buffer)

    context_stack: List[tuple] = []  # (name, indent)
    triple_buffer = None  # (delim, start_idx, collected_str)

    def current_context_path() -> List[str]:
        return [c[0] for c in context_stack]

    for idx, line in enumerate(logical_lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Context pop
        while context_stack and indent < context_stack[-1][1]:
            context_stack.pop()

        # Triple quote devam
        if triple_buffer:
            delim, start_idx, collected = triple_buffer
            collected += ("\n" if collected else "") + stripped
            if delim in stripped:
                body, _, _ = collected.partition(delim)
                for para in body.split("\n\n"):
                    text = para.strip()
                    if not text:
                        continue
                    protected, ph = protect_placeholders(text)
                    entries.append(
                        {
                            "text": restore_placeholders(protected, ph),
                            "raw_text": f"{delim}" + body + f"{delim}",
                            "line_number": start_idx + 1,
                            "context_line": text,
                            "text_type": "monologue",
                            "file_path": file_path,
                            "context_path": current_context_path(),
                        }
                    )
                triple_buffer = None
            else:
                triple_buffer = (delim, start_idx, collected)
            continue

        if not stripped or stripped.startswith("#") or any(
            stripped.startswith(p) for p in TECHNICAL_PREFIXES
        ):
            continue

        # --- v2.5.0: Extract strings from default dict/list literals and loose strings ---
        # Handles: default quest = {"anna": ["Start by helping...", ...]}
        # Also handles lines inside brackets: "Start by helping her..."
        
        # v2.5.1: More robust string literal regex to avoid escaping issues
        # default_strings_re artık döngü dışında derleniyor — her satır için re.compile() yok
        
        if stripped.startswith("default ") or not re.match(r'^[a-zA-Z_]', stripped):
            found_any = False
            # Check Character definitions - skip these as they are usually handled by dialogue/character regex
            if 'Character(' in stripped or 'Character (' in stripped:
                pass
            elif re.match(r'^default\s+\w+\s*=\s*(?:True|False|None|\d+|[\d.]+)\s*$', stripped):
                pass
            else:
                for sm in _default_strings_re.finditer(stripped):
                    q = sm.group(0)
                    # Safe stripping of quotes
                    if len(q) < 2: continue
                    text_content = q[1:-1]
                    
                    # Basic filters
                    if not text_content or len(text_content.strip()) < 2:
                        continue

                    visible_text = normalize_visible_text(text_content)
                    if not visible_text:
                        continue
                        
                    if re.match(r'^[a-zA-Z0-9_/\\.-]+\.(png|jpg|mp3|ogg|rpy|rpyc|webp|gif)$', text_content, re.I):
                        continue
                        
                    # Skip internal Ren'Py paths or technical IDs
                    if text_content.islower() and len(text_content) < 20 and ' ' not in text_content and not text_content.startswith('{'):
                         # v2.7.2: Skip common internal states (playing, waiting, etc.)
                         # Only accept if it has punctuation, spaces, or starts with caps (usually handle above)
                         if not re.search(r'[^a-zA-Z0-9_]', text_content):
                              continue
                    
                    # Meaningful alphabetic content check
                    cleaned = normalize_visible_text(text_content).replace('\\n', ' ').strip()
                    if len(cleaned) < 2 and '{' not in text_content:
                        continue
                        
                    if not any(ch.isalpha() for ch in cleaned) and '{' not in text_content:
                        continue
                    
                    # protect_placeholders handles internal [var] and {tag}
                    protected, ph = protect_placeholders(text_content)
                    entries.append(
                        {
                            "text": restore_placeholders(protected, ph),
                            "raw_text": q,
                            "line_number": idx + 1,
                            "context_line": line[:500],
                            "text_type": "data_string",
                            "file_path": file_path,
                            "context_path": current_context_path(),
                        }
                    )
                    found_any = True
                
                # If it was a 'default' line, we must stop here to avoid falling into dialogue/narrator logic
                # which often misinterprets technical assignments.
                if stripped.startswith("default ") or (found_any and not re.match(r'^[a-zA-Z_]', stripped)):
                    continue
        # --- End data string handling ---

        # Skip translate blocks (already translated content) - v2.4.1
        if stripped.startswith("translate "):
            # Enter translate block - skip until dedent
            context_stack.append(("translate", indent))
            continue
        
        # If we're in a translate block, skip content until we exit
        if context_stack and context_stack[-1][0] == "translate":
            continue

        # Blok başlangıçları
        if stripped.startswith("label "):
            tokens = stripped.split()
            if len(tokens) > 1:
                label_name = tokens[1].split(":")[0]
                context_stack.append((f"label:{label_name}", indent))
            continue
        if stripped.startswith("screen "):
            tokens = stripped.split()
            if len(tokens) > 1:
                screen_name = tokens[1].split(":")[0]
                context_stack.append((f"screen:{screen_name}", indent))
        if stripped.startswith("transform "):
            tokens = stripped.split()
            if len(tokens) > 1:
                trans_name = tokens[1].split(":")[0]
                context_stack.append((f"transform:{trans_name}", indent))
        if stripped.startswith("menu"):
            context_stack.append(("menu", indent))
        if stripped.startswith("python") or stripped.startswith("init python") or stripped.startswith("$"):
            context_stack.append(("python", indent))
        
        # NEW v2.4.1: NVL mode context
        if stripped.startswith("nvl"):
            context_stack.append(("nvl", indent))
        
        # NEW v2.4.1: Window/frame context for better UI classification
        if stripped.startswith(("window", "frame", "vbox", "hbox")):
            block_type = stripped.split()[0].split(":")[0]
            context_stack.append((f"ui:{block_type}", indent))

        # Triple quote açılışı
        m_triple = triple_start_re.match(stripped)
        if m_triple:
            triple_buffer = (m_triple.group("delim"), idx, m_triple.group("body"))
            continue

        # Menü seçenekleri
        m_menu = menu_choice_re.match(stripped)
        if m_menu:
            q = m_menu.group("quote")
            visible_text = normalize_visible_text(q[1:-1])
            if not visible_text:
                continue
            protected, ph = protect_placeholders(q[1:-1])
            q_raw = m_menu.group("quote")
            entries.append(
                {
                    "text": restore_placeholders(protected, ph),
                    "raw_text": q_raw,
                    "line_number": idx + 1,
                    "context_line": line,
                    "text_type": "menu",
                    "file_path": file_path,
                    "context_path": current_context_path(),
                }
            )
            continue

        # Screen ve ATL elemanları
        if context_stack and context_stack[-1][0].startswith(("screen", "transform")):
            for sm in screen_elem_re.finditer(stripped):
                q = sm.group("quote")
                visible_text = normalize_visible_text(q[1:-1])
                if not visible_text:
                    continue
                protected, ph = protect_placeholders(q[1:-1])
                q_raw = sm.group("quote")
                entries.append(
                    {
                        "text": restore_placeholders(protected, ph),
                        "raw_text": q_raw,
                        "line_number": idx + 1,
                        "context_line": line,
                        "text_type": sm.group(1),
                        "file_path": file_path,
                        "context_path": current_context_path(),
                    }
                )

        # Python _() çağrıları
        if context_stack and context_stack[-1][0] == "python":
            m_py = python_call_re.search(stripped)
            if m_py:
                q = m_py.group("quote")
                visible_text = normalize_visible_text(q[1:-1])
                if not visible_text:
                    continue
                protected, ph = protect_placeholders(q[1:-1])
                q_raw = m_py.group("quote")
                entries.append(
                    {
                        "text": restore_placeholders(protected, ph),
                        "raw_text": q_raw,
                        "line_number": idx + 1,
                        "context_line": line,
                        "text_type": "python_translatable",
                        "file_path": file_path,
                        "context_path": current_context_path(),
                    }
                )
                continue
            # renpy.say/notify içindeki metinler
            m_notify = notify_call_re.search(stripped)
            if m_notify:
                q = m_notify.group("quote")
                visible_text = normalize_visible_text(q[1:-1])
                if not visible_text:
                    continue
                protected, ph = protect_placeholders(q[1:-1])
                q_raw = m_notify.group("quote")
                entries.append(
                    {
                        "text": restore_placeholders(protected, ph),
                        "raw_text": q_raw,
                        "line_number": idx + 1,
                        "context_line": line,
                        "text_type": "python_notify",
                        "file_path": file_path,
                        "context_path": current_context_path(),
                    }
                )
                continue
            # renpy.input varsayılan metin
            m_input = input_call_re.search(stripped)
            if m_input:
                q = m_input.group("quote")
                visible_text = normalize_visible_text(q[1:-1])
                if not visible_text:
                    continue
                protected, ph = protect_placeholders(q[1:-1])
                q_raw = m_input.group("quote")
                entries.append(
                    {
                        "text": restore_placeholders(protected, ph),
                        "raw_text": q_raw,
                        "line_number": idx + 1,
                        "context_line": line,
                        "text_type": "python_input",
                        "file_path": file_path,
                        "context_path": current_context_path(),
                    }
                )
                continue
            # Text("...") displayable
            m_text_disp = text_displayable_re.search(stripped)
            if m_text_disp:
                q = m_text_disp.group("quote")
                visible_text = normalize_visible_text(q[1:-1])
                if not visible_text:
                    continue
                protected, ph = protect_placeholders(q[1:-1])
                q_raw = m_text_disp.group("quote")
                entries.append(
                    {
                        "text": restore_placeholders(protected, ph),
                        "raw_text": q_raw,
                        "line_number": idx + 1,
                        "context_line": line,
                        "text_type": "text_displayable",
                        "file_path": file_path,
                        "context_path": current_context_path(),
                    }
                )
                continue
            continue

        # Karakterli diyalog
        m_dialog = dialog_re.match(stripped)
        if m_dialog:
            q = m_dialog.group("quote")
            visible_text = normalize_visible_text(q[1:-1])
            if not visible_text:
                continue
            protected, ph = protect_placeholders(q[1:-1])
            q_raw = m_dialog.group("quote")
            character = m_dialog.group("char")
            if character and len(character) >= 2 and character[0] == character[-1] and character[0] in ('"', "'"):
                character = character[1:-1]
            entries.append(
                {
                    "text": restore_placeholders(protected, ph),
                    "raw_text": q_raw,
                    "line_number": idx + 1,
                    "context_line": line,
                    "text_type": "dialogue",
                    "character": character,
                    "file_path": file_path,
                    "context_path": current_context_path(),
                }
            )
            continue

        # Narrator
        m_narr = narrator_re.match(stripped)
        if m_narr:
            q = m_narr.group("quote")
            visible_text = normalize_visible_text(q[1:-1])
            if not visible_text:
                continue
            protected, ph = protect_placeholders(q[1:-1])
            q_raw = m_narr.group("quote")
            entries.append(
                {
                    "text": restore_placeholders(protected, ph),
                    "raw_text": q_raw,
                    "line_number": idx + 1,
                    "context_line": line,
                    "text_type": "narration",
                    "file_path": file_path,
                    "context_path": current_context_path(),
                }
            )
            continue

    return entries
