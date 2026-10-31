import openpyxl
import json
import os

wb_path = '09_REVIEW/KTMA_WORKBOOK_001/CANDIDATE_KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx'
wb = openpyxl.load_workbook(wb_path, data_only=False)

defined_names_list = []
try:
    for dn in wb.defined_names.values():
        defined_names_list.append(str(dn))
except Exception as e:
    defined_names_list = [str(e)]

model = {
    'workbook': wb_path,
    'sheetnames': wb.sheetnames,
    'defined_names': defined_names_list,
    'sheets': {}
}

for name in wb.sheetnames:
    sheet = wb[name]
    cells_data = {}
    formulas = []
    
    for row in sheet.iter_rows(values_only=False):
        for cell in row:
            if cell.value is not None:
                val_str = str(cell.value)
                is_formula = val_str.startswith('=')
                if is_formula:
                    formulas.append({
                        'coord': cell.coordinate,
                        'formula': val_str
                    })
                cells_data[cell.coordinate] = {
                    'row': cell.row,
                    'col': cell.column,
                    'type': cell.data_type,
                    'value': cell.value,
                    'number_format': cell.number_format,
                    'is_formula': is_formula
                }
                
    model['sheets'][name] = {
        'max_row': sheet.max_row,
        'max_col': sheet.max_column,
        'merged_ranges': [str(r) for r in sheet.merged_cells.ranges],
        'total_non_empty_cells': len(cells_data),
        'formula_count': len(formulas),
        'formulas_sample': formulas[:100],
        'cells': cells_data
    }

out_json = '09_REVIEW/KTMA_WORKBOOK_001/candidate_structural_model.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(model, f, ensure_ascii=False, indent=2, default=str)

print(f'Candidate structural model successfully written to {out_json}')
