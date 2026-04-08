#!/usr/bin/env python3
"""
PDF 文本提取脚本 - 基于 PyMuPDF
"""

import sys
import json
import fitz  # PyMuPDF

def extract_text(file_path, pages=None, format='markdown'):
    """提取 PDF 文本"""
    try:
        doc = fitz.open(file_path)
        
        total_pages = len(doc)
        
        # 确定要提取的页码
        if pages:
            page_nums = [int(p) - 1 for p in pages.split(',')]  # 转换为 0-based
            page_nums = [p for p in page_nums if 0 <= p < total_pages]
        else:
            page_nums = range(total_pages)
        
        # 提取文本
        content = ""
        for page_num in page_nums:
            page = doc[page_num]
            text = page.get_text()
            
            if format == 'markdown':
                # 添加页码标记
                content += f"\n\n---\n\n**第 {page_num + 1} 页**\n\n"
                content += text
            else:
                content += text
        
        doc.close()
        
        return {
            'success': True,
            'content': content.strip(),
            'page_count': len(page_nums),
            'total_pages': total_pages
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    args = sys.argv[1:]
    file_path = args[0].strip('"')
    
    pages = None
    format = 'markdown'
    
    i = 1
    while i < len(args):
        if args[i] == '--pages' and i + 1 < len(args):
            pages = args[i + 1]
            i += 2
        elif args[i] == '--format' and i + 1 < len(args):
            format = args[i + 1]
            i += 2
        else:
            i += 1
    
    result = extract_text(file_path, pages, format)
    print(json.dumps(result, ensure_ascii=False))
