import json

model_path = '09_REVIEW/KTMA_WORKBOOK_001/ph1_structural_model.json'
with open(model_path, 'r', encoding='utf-8') as f:
    model = json.load(f)

print("Workbook:", model['workbook'])
print("Sheetnames:", model['sheetnames'])
print("Defined names:", model['defined_names'])

for name, sdata in model['sheets'].items():
    print(f"\n--- Sheet: {name} ---")
    print(f"Max row: {sdata['max_row']}, Max col: {sdata['max_col']}")
    print(f"Total non-empty cells: {sdata['total_non_empty_cells']}")
    print(f"Formula count: {sdata['formula_count']}")
    print(f"Merged ranges: {sdata['merged_ranges']}")
    print("Sample formulas:")
    for f_item in sdata['formulas_sample'][:10]:
        print(f"  {f_item['coord']}: {f_item['formula']}")
