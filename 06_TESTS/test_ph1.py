import importlib.util
import sys

# Load ph1_logic.py dynamically
spec = importlib.util.spec_from_file_location("ph1_logic", "05_SRC/ph1_logic.py")
ph1_logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ph1_logic)

def test_align_data():
    eplaza = {"100": {"val": 10}, "200": {"val": 20}}
    impulsa = {"200": {"val": 25}, "300": {"val": 30}}
    
    aligned = ph1_logic.align_data(eplaza, impulsa)
    
    assert "100" in aligned
    assert "200" in aligned
    assert "300" in aligned
    assert aligned["200"]["eplaza"]["val"] == 20
    assert aligned["200"]["impulsa"]["val"] == 25
    print("test_align_data passed")

if __name__ == "__main__":
    test_align_data()
