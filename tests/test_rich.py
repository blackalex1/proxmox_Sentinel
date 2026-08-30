import sys
import os
import pytest

# Add bot to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot')))

from core.rich import (
    build_rich_message,
    _parse_html_table,
    parse_to_rich_text,
    RichBlockTableCell,
    InputRichBlockTable,
    InputRichBlockDetails,
    InputRichBlockSectionHeading,
    InputRichBlockParagraph,
    InputRichMessage,
)

def test_html_table_parsing_basic():
    html_content = (
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th colspan="2" align="center"><b>📊 Status Title</b></th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left">👤 User</td>\n'
        '    <td align="right"><code>admin</code></td>\n'
        '  </tr>\n'
        '</table>'
    )
    
    table_block = _parse_html_table(html_content)
    assert table_block is not None
    assert isinstance(table_block, InputRichBlockTable)
    assert table_block.is_bordered is True
    assert table_block.is_striped is True
    assert len(table_block.cells) == 2
    
    # Check Header Row
    header_row = table_block.cells[0]
    assert len(header_row) == 1
    assert header_row[0].is_header is True
    assert header_row[0].colspan == 2
    assert header_row[0].align == "center"
    assert "Status Title" in str(header_row[0].text)
    
    # Check Data Row
    data_row = table_block.cells[1]
    assert len(data_row) == 2
    assert data_row[0].align == "left"
    assert "User" in str(data_row[0].text)
    assert data_row[1].align == "right"
    assert "admin" in str(data_row[1].text)


def test_build_rich_message_with_table_and_details():
    full_text = (
        '⚡ <b>Security Alert</b>\n'
        '<table bordered striped compact>\n'
        '  <tr>\n'
        '    <th align="center">IP</th>\n'
        '    <th align="center">Action</th>\n'
        '  </tr>\n'
        '  <tr>\n'
        '    <td align="left"><code>192.168.1.100</code></td>\n'
        '    <td align="left">Blocked</td>\n'
        '  </tr>\n'
        '</table>\n\n'
        '<details>\n'
        '  <summary>📋 Event Details</summary>\n'
        '  <pre><code>Connection attempt on port 22</code></pre>\n'
        '</details>'
    )
    
    msg = build_rich_message(full_text)
    assert isinstance(msg, InputRichMessage)
    assert len(msg.blocks) == 3
    
    # 1. Paragraph / text block
    assert isinstance(msg.blocks[0], InputRichBlockParagraph)
    assert "Security Alert" in str(msg.blocks[0].text)
    
    # 2. Table block
    assert isinstance(msg.blocks[1], InputRichBlockTable)
    assert len(msg.blocks[1].cells) == 2
    
    # 3. Details block
    assert isinstance(msg.blocks[2], InputRichBlockDetails)
    assert "Event Details" in str(msg.blocks[2].summary)
    assert "Connection attempt on port 22" in str(msg.blocks[2].blocks[0].text)


def test_build_rich_message_with_headings():
    full_text = (
        '### 🚨 Critical Alert\n'
        'A high-severity threat has been detected.'
    )
    msg = build_rich_message(full_text)
    assert len(msg.blocks) == 2
    assert isinstance(msg.blocks[0], InputRichBlockSectionHeading)
    assert msg.blocks[0].size == 2
    assert "Critical Alert" in str(msg.blocks[0].text)
    assert isinstance(msg.blocks[1], InputRichBlockParagraph)
    assert "high-severity threat" in str(msg.blocks[1].text)


