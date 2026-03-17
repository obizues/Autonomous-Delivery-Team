from validators import is_valid_record


def process_records(records: list[dict]) -> dict:
    accepted: list[dict] = []
    rejected: list[dict] = []

    for record in records:
        if is_valid_record(record):
            accepted.append({
                "id": record["id"],
                "amount": float(record["amount"]),
                "status": "processed",
            })
        else:
            rejected.append(record)

    return {
        "accepted": accepted,
        "rejected": rejected,
    }
