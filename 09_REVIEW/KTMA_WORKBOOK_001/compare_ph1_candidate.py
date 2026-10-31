import json

ph1_path = '09_REVIEW/KTMA_WORKBOOK_001/ph1_structural_model.json'
cand_path = '09_REVIEW/KTMA_WORKBOOK_001/candidate_structural_model.json'

with open(ph1_path, 'r', encoding='utf-8') as f:
    ph1 = json.load(f)

with open(cand_path, 'r', encoding='utf-8') as f:
    cand = json.load(f)

comparison = {
    'ph1_sheets': ph1['sheetnames'],
    'candidate_sheets': cand['sheetnames'],
    'sheet_comparisons': {}
}

# Common sheets comparison
common_sheets = set(ph1['sheetnames']).intersection(set(cand['sheetnames']))
for sheet in common_sheets:
    p_cells = ph1['sheets'][sheet]['cells']
    c_cells = cand['sheets'][sheet]['cells']
    
    p_keys = set(p_cells.keys())
    c_keys = set(c_cells.keys())
    
    common_coords = p_keys.intersection(c_keys)
    only_in_ph1 = p_keys - c_keys
    only_in_cand = c_keys - p_keys
    
    mismatches = []
    for coord in common_coords:
        pval = p_cells[coord]['value']
        cval = c_cells[coord]['value']
        if str(pval) != str(cval):
            mismatches.append({
                'coord': coord,
                'ph1_value': pval,
                'candidate_value': cval
            })
            
    comparison['sheet_comparisons'][sheet] = {
        'common_cell_count': len(common_coords),
        'only_in_ph1_count': len(only_in_ph1),
        'only_in_cand_count': len(only_in_cand),
        'mismatch_count': len(mismatches),
        'mismatches_sample': mismatches[:50]
    }

added_sheets = set(cand['sheetnames']) - set(ph1['sheetnames'])
comparison['added_sheets'] = list(added_sheets)

out_json = '09_REVIEW/KTMA_WORKBOOK_001/cell_comparison_matrix.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(comparison, f, ensure_ascii=False, indent=2, default=str)

print(f'Cell comparison matrix successfully written to {out_json}')
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'mismatches_sample'} for k, v in comparison['sheet_comparisons'].items()}, indent=2))
print('Added sheets:', added_sheets)
