def is_valid_record(record: dict) -> bool:
    if "id" not in record:
        return False
    if "amount" not in record:
        return False
    return True
