#!/usr/bin/env python3
"""
获取 PDF 元数据
"""

import sys
import json
import fitz  # PyMuPDF

def get_info(file_path):
    """获取 PDF 信息"""
    try:
        doc = fitz.open(file_path)
        
        info = {
            'success': True,
            'file': file_path,
            'page_count': len(doc),
            'metadata': {}
        }
        
        # 获取元数据
        metadata = doc.metadata
        if metadata.get('title'):
            info['metadata']['title'] = metadata['title']
        if metadata.get('author'):
            info['metadata']['author'] = metadata['author']
        if metadata.get('creationDate'):
            info['metadata']['creationDate'] = metadata['creationDate']
        if metadata.get('modificationDate'):
            info['metadata']['modificationDate'] = metadata['modificationDate']
        if metadata.get('creator'):
            info['metadata']['creator'] = metadata['creator']
        if metadata.get('producer'):
            info['metadata']['producer'] = metadata['producer']
        
        doc.close()
        return info
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    file_path = sys.argv[1].strip('"')
    result = get_info(file_path)
    print(json.dumps(result, ensure_ascii=False))
