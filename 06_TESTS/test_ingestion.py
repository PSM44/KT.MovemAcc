import json

def test_ingestion_contract():
    with open('04_CONFIG/INGESTION_CONTRACT.json', 'r') as f:
        contract = json.load(f)
    
    assert len(contract) > 0
    assert "contract_id" in contract[0]
    print("test_ingestion_contract passed")

if __name__ == "__main__":
    test_ingestion_contract()
