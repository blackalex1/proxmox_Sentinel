# bot/core/rich.py
"""
Модуль поддержки нативных Rich Messages (Telegram Bot API 10.1 - 10.3).
Предоставляет парсер текстовой разметки в структуры RichTextUnion и конвертер
Markdown/HTML документов в валидный список блоков InputRichMessage.
"""

import re
from typing import Union, List, Any

from aiogram.types import (
    InputRichMessage,
    InputRichBlockSectionHeading,
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockTable,
    RichBlockTableCell,
    InputRichBlockDetails,
    InputRichBlockPreformatted,
    InputRichBlockList,
    InputRichBlockListItem,
    RichTextBold,
    RichTextCode,
    RichTextItalic,
    RichTextUnderline,
    RichTextStrikethrough,
    RichTextSpoiler,
    RichTextUrl,
    RichTextUnion,
)


def parse_to_rich_text(text: str) -> RichTextUnion:
    """
    Парсит строку с HTML-тегами (<b>, <code>, <i>, <u>, <s>, <tg-spoiler>, <a href=...>)
    или Markdown-нотацией (**...**, `...`, *...*) в нативную структуру RichTextUnion.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        return str(text)

    # Нормализуем markdown в HTML для единообразного токенизатора
    s = text
    # 1. `code` -> <code>code</code>
    s = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', s)
    # 2. **bold** -> <b>bold</b>
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    # 3. *italic* -> <i>italic</i>
    s = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', s)

    # Регулярка для тегов
    tag_pattern = re.compile(r'<(/?[a-zA-Z0-9_-]+)(?:\s+href=["\']([^"\']+)["\'])?[^>]*>')
    
    tokens = []
    stack = []  # [(tag, attr, [children])]
    
    pos = 0
    for match in tag_pattern.finditer(s):
        start, end = match.span()
        if start > pos:
            plain = s[pos:start]
            if stack:
                stack[-1][2].append(plain)
            else:
                tokens.append(plain)
                
        tag_name = match.group(1).lower()
        href = match.group(2)
        
        if not tag_name.startswith('/'):
            # Open tag
            stack.append((tag_name, href, []))
        else:
            # Close tag
            closing = tag_name[1:]
            if stack and stack[-1][0] == closing:
                tag, attr, children = stack.pop()
                # Resolve children
                inner = children[0] if len(children) == 1 and isinstance(children[0], str) else children
                if isinstance(inner, list) and len(inner) == 1:
                    inner = inner[0]
                
                node = None
                if tag in ('b', 'strong'):
                    node = RichTextBold(text=inner)
                elif tag in ('code',):
                    node = RichTextCode(text=inner if isinstance(inner, str) else str(inner))
                elif tag in ('i', 'em'):
                    node = RichTextItalic(text=inner)
                elif tag in ('u', 'ins'):
                    node = RichTextUnderline(text=inner)
                elif tag in ('s', 'strike', 'del'):
                    node = RichTextStrikethrough(text=inner)
                elif tag in ('tg-spoiler', 'spoiler'):
                    node = RichTextSpoiler(text=inner)
                elif tag == 'a' and attr:
                    node = RichTextUrl(text=inner if isinstance(inner, str) else str(inner), url=attr)
                else:
                    node = inner

                if stack:
                    stack[-1][2].append(node)
                else:
                    tokens.append(node)
        pos = end

    if pos < len(s):
        plain = s[pos:]
        if stack:
            stack[-1][2].append(plain)
        else:
            tokens.append(plain)

    # Если остались незакрытые теги в стеке, объединяем всё
    while stack:
        tag, attr, children = stack.pop()
        inner = children[0] if len(children) == 1 else children
        if stack:
            stack[-1][2].extend(children)
        else:
            if isinstance(inner, list):
                tokens.extend(inner)
            else:
                tokens.append(inner)

    if not tokens:
        return ""
    if len(tokens) == 1 and isinstance(tokens[0], (str, RichTextBold, RichTextCode, RichTextItalic, RichTextUnderline, RichTextStrikethrough, RichTextSpoiler, RichTextUrl)):
        return tokens[0]
    return tokens


def _detect_code_language(code_text: str, explicit_lang: str = None) -> str:
    """Определяет язык подсветки для блока кода."""
    if explicit_lang:
        lang = explicit_lang.lower().strip()
        if lang in ('bash', 'sh', 'shell'):
            return 'bash'
        if lang in ('py', 'python'):
            return 'python'
        if lang in ('json', 'js', 'diff', 'sql', 'yaml', 'yml', 'html', 'xml', 'c', 'cpp', 'rust', 'go'):
            return lang
    
    # Автодетект по содержимому
    trimmed = code_text.strip()
    if trimmed.startswith('{') and trimmed.endswith('}'):
        return 'json'
    if trimmed.startswith('---') and '+++' in trimmed:
        return 'diff'
    if any(trimmed.startswith(x) for x in ('SRC=', 'DST=', 'Aug ', 'Sep ', 'Oct ', 'Nov ', 'Dec ', 'Jan ', 'Feb ', 'Mar ', 'Apr ', 'May ', 'Jun ', 'Jul ')):
        return 'bash'
    if 'iptables' in trimmed or 'systemctl' in trimmed or 'sshd' in trimmed:
        return 'bash'
    return 'bash'


def build_rich_message(content: Any) -> InputRichMessage:
    """
    Преобразует произвольный контент (InputRichMessage, список блоков, или строку Markdown/HTML)
    в полноценный валидный объект InputRichMessage с блоками.
    """
    if isinstance(content, InputRichMessage):
        return content
    if isinstance(content, list):
        return InputRichMessage(blocks=content)
    if not isinstance(content, str):
        content = str(content)

    blocks = []
    
    # 1. Извлекаем <details><summary>...</summary>...</details>
    details_pattern = re.compile(
        r'<details\b[^>]*>\s*<summary\b[^>]*>(.*?)</summary>(.*?)</details>',
        flags=re.DOTALL | re.IGNORECASE
    )
    
    segments = []
    last_idx = 0
    for m in details_pattern.finditer(content):
        start, end = m.span()
        if start > last_idx:
            segments.append(('text', content[last_idx:start]))
        segments.append(('details', m.group(1).strip(), m.group(2).strip()))
        last_idx = end
    if last_idx < len(content):
        segments.append(('text', content[last_idx:]))

    for seg in segments:
        if seg[0] == 'details':
            summary_raw = seg[1]
            body_raw = seg[2]
            
            # Извлекаем code внутри details если есть
            code_m = re.search(r'<pre\b[^>]*>\s*<code(?:\s+class=["\'](?:language-)?([a-zA-Z0-9_-]+)["\'])?[^>]*>(.*?)</code>\s*</pre>', body_raw, flags=re.DOTALL | re.IGNORECASE)
            inner_blocks = []
            if code_m:
                lang = _detect_code_language(code_m.group(2), code_m.group(1))
                inner_blocks.append(InputRichBlockPreformatted(text=code_m.group(2).strip(), language=lang))
            else:
                # Markdown code block ```lang ... ```
                md_code_m = re.search(r'```([a-zA-Z0-9_-]*)\n([\s\S]*?)```', body_raw)
                if md_code_m:
                    lang = _detect_code_language(md_code_m.group(2), md_code_m.group(1))
                    inner_blocks.append(InputRichBlockPreformatted(text=md_code_m.group(2).strip(), language=lang))
                else:
                    clean_body = re.sub(r'</?[a-zA-Z0-9_-]+[^>]*>', '', body_raw).strip()
                    if clean_body:
                        inner_blocks.append(InputRichBlockParagraph(text=parse_to_rich_text(clean_body)))
            
            if not inner_blocks:
                inner_blocks.append(InputRichBlockParagraph(text="..."))

            blocks.append(
                InputRichBlockDetails(
                    summary=parse_to_rich_text(summary_raw),
                    is_open=False,
                    blocks=inner_blocks
                )
            )
            continue

        # Обрабатываем обычный текстовый сегмент
        text_content = seg[1].strip()
        if not text_content:
            continue

        lines = text_content.split('\n')
        current_table_lines = []
        current_paragraph_lines = []

        def flush_table():
            nonlocal current_table_lines
            if not current_table_lines:
                return
            table_cells = []
            header_processed = False
            for r_line in current_table_lines:
                r_trimmed = r_line.strip()
                if not (r_trimmed.startswith('|') and r_trimmed.endswith('|')):
                    continue
                parts = [p.strip() for p in r_trimmed.strip('|').split('|')]
                if any(p.startswith(':--') or p.startswith('---') or p.startswith(':-:') for p in parts):
                    header_processed = True
                    continue
                
                row_cells = []
                is_hdr = not header_processed and len(table_cells) == 0
                for c_idx, cell_text in enumerate(parts):
                    cell_is_header = is_hdr or (c_idx == 0 and len(parts) == 2)
                    row_cells.append(
                        RichBlockTableCell(
                            text=parse_to_rich_text(cell_text),
                            align="left",
                            valign="middle",
                            is_header=cell_is_header
                        )
                    )
                if row_cells:
                    table_cells.append(row_cells)
            
            if table_cells:
                blocks.append(
                    InputRichBlockTable(
                        is_bordered=True,
                        is_striped=True,
                        cells=table_cells
                    )
                )
            current_table_lines = []

        def flush_paragraph():
            nonlocal current_paragraph_lines
            if not current_paragraph_lines:
                return
            p_text = '\n'.join(current_paragraph_lines).strip()
            if p_text:
                blocks.append(InputRichBlockParagraph(text=parse_to_rich_text(p_text)))
            current_paragraph_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            trimmed = line.strip()

            # 1. Заголовки: # Title, ## Title, ### Title
            h1_m = re.match(r'^#\s+(.+)$', trimmed)
            if h1_m:
                flush_paragraph()
                flush_table()
                blocks.append(InputRichBlockSectionHeading(text=parse_to_rich_text(h1_m.group(1).strip()), size=1))
                i += 1
                continue

            h2_m = re.match(r'^#{2,3}\s+(.+)$', trimmed)
            if h2_m:
                flush_paragraph()
                flush_table()
                blocks.append(InputRichBlockSectionHeading(text=parse_to_rich_text(h2_m.group(1).strip()), size=2))
                i += 1
                continue

            # 2. Разделитель: --- или ⎯⎯⎯⎯ или <hr>
            if re.match(r'^(?:---|⎯+|—+|<hr\s*/?>)$', trimmed):
                flush_paragraph()
                flush_table()
                blocks.append(InputRichBlockDivider())
                i += 1
                continue

            # 3. Блок кода: ```lang ... ```
            if trimmed.startswith('```'):
                flush_paragraph()
                flush_table()
                lang_tag = trimmed[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines) and lines[i].strip().startswith('```'):
                    i += 1
                code_str = '\n'.join(code_lines)
                lang = _detect_code_language(code_str, lang_tag)
                blocks.append(InputRichBlockPreformatted(text=code_str, language=lang))
                continue

            # 4. Таблица Markdown: | Col1 | Col2 |
            if trimmed.startswith('|') and trimmed.endswith('|'):
                flush_paragraph()
                current_table_lines.append(trimmed)
                i += 1
                continue
            else:
                if current_table_lines:
                    flush_table()

            # 5. Пустые строки
            if not trimmed:
                if current_paragraph_lines:
                    flush_paragraph()
                i += 1
                continue

            # 6. Обычные строки параграфа
            current_paragraph_lines.append(line)
            i += 1

        flush_paragraph()
        flush_table()

    if not blocks:
        blocks.append(InputRichBlockParagraph(text=parse_to_rich_text(content)))

    return InputRichMessage(blocks=blocks)
