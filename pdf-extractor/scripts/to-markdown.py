#!/usr/bin/env python3
"""
PDF 转 Markdown
"""

import sys
import json
import fitz  # PyMuPDF

def to_markdown(file_path, output_path=None):
    """转换 PDF 为 Markdown"""
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        
        markdown = f"# {doc.metadata.get('title', 'PDF 文档')}\n\n"
        
        if doc.metadata.get('author'):
            markdown += f"**作者**: {doc.metadata['author']}\n\n"
        
        markdown += "---\n\n"
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            
            # 添加页码
            markdown += f"\n\n## 第 {page_num + 1} 页\n\n"
            markdown += text
        
        doc.close()
        
        result = {
            'success': True,
            'content': markdown,
            'pages': total_pages
        }
        
        # 如果指定了输出文件，保存
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            result['output_file'] = output_path
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    args = sys.argv[1:]
    file_path = args[0].strip('"')
    
    output_path = None
    i = 1
    while i < len(args):
        if args[i] == '--output' and i + 1 < len(args):
            output_path = args[i + 1].strip('"')
            i += 2
        else:
            i += 1
    
    result = to_markdown(file_path, output_path)
    print(json.dumps(result, ensure_ascii=False))
