import pandas as pd
from pyxlsb import open_workbook

def parse_raw(file_path):
    print(f"Opening {file_path}")
    try:
        with open_workbook(file_path) as wb:
            # Just print sheet names to verify it opens correctly
            print("Sheets:", wb.sheets)
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Use one of the real files
    result = parse_raw("RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb")
    print(f"Result: {result}")
