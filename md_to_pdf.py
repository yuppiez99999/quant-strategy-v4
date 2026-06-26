#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 转 HTML/PDF 转换器
使用浏览器打印功能生成 PDF
"""

import sys
import os
from pathlib import Path


def markdown_to_html(md_file: str, output_html: str = None) -> str:
    """
    将 Markdown 文件转换为精美的 HTML
    
    Args:
        md_file: Markdown 文件路径
        output_html: 输出 HTML 文件路径（可选）
    
    Returns:
        HTML 文件路径
    """
    # 读取 Markdown 内容
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 简单的 Markdown 转 HTML（基础版本）
    html_content = convert_markdown_to_html(md_content)
    
    # 如果未指定输出文件，使用相同名称
    if output_html is None:
        output_html = md_file.replace('.md', '.html')
    
    # 写入 HTML 文件
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML 文件已生成: {output_html}")
    return output_html


def convert_markdown_to_html(md_text: str) -> str:
    """
    将 Markdown 文本转换为 HTML（支持常用语法）
    """
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_table = False
    table_headers_done = False
    
    html_lines.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量化策略报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 1em;
            padding-bottom: 0.5em;
            border-bottom: 3px solid #2c3e50;
            color: #2c3e50;
        }
        
        h2 {
            font-size: 1.8em;
            margin-top: 1.5em;
            margin-bottom: 0.8em;
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        
        h3 {
            font-size: 1.4em;
            margin-top: 1.2em;
            margin-bottom: 0.6em;
            color: #2c3e50;
        }
        
        p {
            margin-bottom: 1em;
            text-align: justify;
        }
        
        ul, ol {
            margin-left: 2em;
            margin-bottom: 1em;
        }
        
        li {
            margin-bottom: 0.5em;
        }
        
        strong {
            color: #2c3e50;
            font-weight: 600;
        }
        
        em {
            color: #7f8c8d;
        }
        
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 0.9em;
        }
        
        pre {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 1em 0;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }
        
        pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
        
        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin: 1em 0;
            color: #7f8c8d;
            font-style: italic;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5em 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        th {
            background: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }
        
        tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        tr:hover {
            background: #e8f4f8;
        }
        
        hr {
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 2em 0;
        }
        
        .emoji {
            font-size: 1.2em;
        }
        
        /* 打印优化 */
        @media print {
            body {
                padding: 20px;
            }
            
            h1 {
                page-break-before: avoid;
            }
            
            h2 {
                page-break-after: avoid;
            }
            
            table {
                page-break-inside: avoid;
            }
            
            pre {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
''')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 代码块
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                html_lines.append('<pre><code>')
            else:
                in_code_block = False
                html_lines.append('</code></pre>')
            i += 1
            continue
        
        if in_code_block:
            html_lines.append(line)
            i += 1
            continue
        
        # 标题
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:].strip()}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:].strip()}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{line[4:].strip()}</h3>')
        
        # 表格
        elif '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_headers_done = False
                html_lines.append('<table>')
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # 检查是否是分隔线
            if all(cell.replace('-', '').replace(':', '').strip() == '' for cell in cells):
                table_headers_done = True
            else:
                if not table_headers_done:
                    html_lines.append('<thead><tr>')
                    for cell in cells:
                        html_lines.append(f'<th>{cell}</th>')
                    html_lines.append('</tr></thead><tbody>')
                else:
                    html_lines.append('<tr>')
                    for cell in cells:
                        html_lines.append(f'<td>{cell}</td>')
                    html_lines.append('</tr>')
        elif in_table:
            # 表格结束
            html_lines.append('</tbody></table>')
            in_table = False
            table_headers_done = False
            # 继续处理当前行
            continue
        
        # 列表
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            if not html_lines or not html_lines[-1].startswith('<ul>'):
                html_lines.append('<ul>')
            item_text = line.strip()[2:]
            html_lines.append(f'<li>{item_text}</li>')
        
        # 有序列表
        elif line.strip() and line.strip()[0].isdigit() and '. ' in line:
            if not html_lines or not html_lines[-1].startswith('<ol>'):
                html_lines.append('<ol>')
            item_text = line.strip().split('. ', 1)[1]
            html_lines.append(f'<li>{item_text}</li>')
        
        # 引用
        elif line.strip().startswith('>'):
            quote_text = line.strip()[1:].strip()
            html_lines.append(f'<blockquote>{quote_text}</blockquote>')
        
        # 水平线
        elif line.strip() == '---' or line.strip() == '***':
            html_lines.append('<hr>')
        
        # 普通段落
        elif line.strip():
            # 处理粗体和斜体
            text = line
            text = text.replace('**', '<strong>').replace('**', '</strong>')
            text = text.replace('*', '<em>').replace('*', '</em>')
            text = text.replace('`', '<code>').replace('`', '</code>')
            html_lines.append(f'<p>{text}</p>')
        
        i += 1
    
    # 关闭未关闭的标签
    if in_table:
        html_lines.append('</tbody></table>')
    if html_lines and html_lines[-1].startswith('<ul>'):
        html_lines.append('</ul>')
    if html_lines and html_lines[-1].startswith('<ol>'):
        html_lines.append('</ol>')
    
    html_lines.append('''
</body>
</html>''')
    
    return '\n'.join(html_lines)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python md_to_pdf.py <markdown文件>")
        print("示例: python md_to_pdf.py report.md")
        sys.exit(1)
    
    md_file = sys.argv[1]
    
    if not os.path.exists(md_file):
        print(f"❌ 文件不存在: {md_file}")
        sys.exit(1)
    
    print(f"📄 正在转换: {md_file}")
    
    # 转换为 HTML
    html_file = markdown_to_html(md_file)
    
    # 自动打开 HTML 文件
    print("\n💡 下一步操作:")
    print("1. HTML 文件已在浏览器中打开")
    print("2. 按 Ctrl+P (或 Cmd+P on Mac)")
    print("3. 选择'另存为 PDF'")
    print("4. 调整边距和选项")
    print("5. 保存 PDF 文件\n")
    
    # 在默认浏览器中打开
    os.startfile(html_file)


if __name__ == '__main__':
    main()
