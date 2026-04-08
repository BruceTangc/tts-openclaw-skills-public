#!/usr/bin/env python3
"""
Excel 图表脚本 - 使用 xlsxwriter 添加图表
"""

import sys
import json
import argparse
import xlsxwriter

def create_chart(file_path, data, chart_type='bar'):
    """
    创建带图表的 Excel
    
    Args:
        file_path: 输出文件路径
        data: 数据（包含标签和值）
        chart_type: 图表类型 bar/line/pie
    """
    try:
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet()
        
        # 写入数据
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                worksheet.write(row_idx, col_idx, value)
        
        # 创建图表
        chart = workbook.add_chart({'type': chart_type})
        
        # 配置图表数据
        max_row = len(data)
        max_col = len(data[0]) if data else 0
        
        if chart_type == 'bar' or chart_type == 'line':
            # 柱状图/折线图
            chart.add_series({
                'name':       f'=Sheet1!$B$1' if max_col > 1 else 'Series 1',
                'categories': f'=Sheet1!$A$2:$A${max_row}',  # 第一列作为分类
                'values':     f'=Sheet1!$B$2:$B${max_row}',  # 第二列作为值
            })
            
            chart.set_title({'name': '数据图表'})
            chart.set_x_axis({'name': '项目'})
            chart.set_y_axis({'name': '数值'})
        
        elif chart_type == 'pie':
            # 饼图
            chart.add_series({
                'name':       '数据分布',
                'categories': f'=Sheet1!$A$2:$A${max_row}',
                'values':     f'=Sheet1!$B$2:$B${max_row}',
                'data_labels': {'percentage': True},
            })
            chart.set_title({'name': '数据分布'})
        
        # 设置图表样式
        chart.set_legend({'position': 'right'})
        
        # 插入图表
        worksheet.insert_chart('D2', chart)
        
        # 自动调整列宽
        for col_idx in range(max_col):
            max_length = max(len(str(row[col_idx])) for row in data if col_idx < len(row))
            worksheet.set_column(col_idx, col_idx, min(max_length + 2, 30))
        
        workbook.close()
        
        return {
            'success': True,
            'output_file': file_path,
            'chart_type': chart_type,
            'row_count': max_row,
            'column_count': max_col
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='创建带图表的 Excel')
    parser.add_argument('--file', required=True, help='输出文件路径')
    parser.add_argument('--data', required=True, help='JSON 格式数据')
    parser.add_argument('--chart-type', default='bar', choices=['bar', 'line', 'pie'], help='图表类型')
    
    args = parser.parse_args()
    data = json.loads(args.data)
    
    result = create_chart(args.file, data, args.chart_type)
    print(json.dumps(result, ensure_ascii=False))
