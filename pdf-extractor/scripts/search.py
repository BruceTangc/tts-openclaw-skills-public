#!/usr/bin/env python3
"""
PDF 内容搜索
"""

import sys
import json
import fitz  # PyMuPDF

def search_pdf(file_path, query, case_sensitive=False):
    """搜索 PDF 内容"""
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        
        matches = []
        
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # 搜索关键词
            text_instances = page.search_for(query)
            
            for inst in text_instances:
                # 获取匹配的文本
                text = page.get_textbox(inst)
                matches.append({
                    'page': page_num + 1,
                    'text': text.strip(),
                    'rect': {
                        'x0': inst.x0,
                        'y0': inst.y0,
                        'x1': inst.x1,
                        'y1': inst.y1
                    }
                })
        
        doc.close()
        
        return {
            'success': True,
            'query': query,
            'total_matches': len(matches),
            'matches': matches[:20]  # 最多返回 20 个匹配
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    args = sys.argv[1:]
    file_path = args[0].strip('"')
    
    query = ""
    case_sensitive = False
    
    i = 1
    while i < len(args):
        if args[i] == '--query' and i + 1 < len(args):
            query = args[i + 1].strip('"')
            i += 2
        elif args[i] == '--case-sensitive':
            case_sensitive = True
            i += 1
        else:
            i += 1
    
    result = search_pdf(file_path, query, case_sensitive)
    print(json.dumps(result, ensure_ascii=False))
