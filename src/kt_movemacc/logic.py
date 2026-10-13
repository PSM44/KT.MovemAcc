def align_data(eplaza_data, impulsa_data):
    """
    Aligns EPLAZA and IMPULSA data.
    Input: dicts keyed by account_code.
    """
    aligned = {}
    all_keys = set(eplaza_data.keys()) | set(impulsa_data.keys())
    for key in all_keys:
        aligned[key] = {
            "eplaza": eplaza_data.get(key),
            "impulsa": impulsa_data.get(key)
        }
    return aligned
