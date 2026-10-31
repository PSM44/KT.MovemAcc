import json

ph1_path = '09_REVIEW/KTMA_WORKBOOK_001/ph1_structural_model.json'
cand_path = '09_REVIEW/KTMA_WORKBOOK_001/candidate_structural_model.json'

with open(ph1_path, 'r', encoding='utf-8') as f:
    ph1 = json.load(f)

with open(cand_path, 'r', encoding='utf-8') as f:
    cand = json.load(f)

mapping = {
    '01_Eplaza_Source': '01_Sources_Eplaza',
    '02_Impulsa_Source': '02_Sources_Impulsa',
    '03_Consolidated_PH1': '03_Consolidated_PH1'
}

detailed_comparison = {}
for ph1_sheet, cand_sheet in mapping.items():
    p_cells = ph1['sheets'][ph1_sheet]['cells']
    c_cells = cand['sheets'][cand_sheet]['cells']
    
    p_keys = set(p_cells.keys())
    c_keys = set(c_cells.keys())
    
    common = p_keys.intersection(c_keys)
    mismatches = []
    for coord in common:
        pval = p_cells[coord]['value']
        cval = c_cells[coord]['value']
        if str(pval) != str(cval):
            mismatches.append({'coord': coord, 'ph1': pval, 'candidate': cval})
            
    detailed_comparison[f"{ph1_sheet} vs {cand_sheet}"] = {
        'ph1_total_cells': len(p_keys),
        'candidate_total_cells': len(c_keys),
        'common_cells': len(common),
        'mismatch_count': len(mismatches),
        'mismatches_sample': mismatches[:20]
    }

out_json = '09_REVIEW/KTMA_WORKBOOK_001/cell_comparison_matrix_v2.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(detailed_comparison, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(detailed_comparison, indent=2, default=lambda x: x[:20] if isinstance(x, list) else x))
