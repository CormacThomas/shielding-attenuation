def convert_activity_to_bq(activity_value: float, activity_unit: str) -> float:
    # Convert activity units to becquerels.
    # Internally, the simulator uses Bq because 1 Bq = 1 decay/s.

    if activity_value < 0:
        raise ValueError("Activity cannot be negative.")

    unit = activity_unit.lower().strip()

    if unit == "bq":
        return activity_value

    if unit == "kbq":
        return activity_value * 1.0e3

    if unit == "mbq":
        return activity_value * 1.0e6

    if unit == "gbq":
        return activity_value * 1.0e9

    if unit == "ci":
        return activity_value * 3.7e10

    if unit == "mci":
        return activity_value * 3.7e7

    if unit == "uci":
        return activity_value * 3.7e4

    raise ValueError(
        "Unsupported activity unit. Use bq, kbq, mbq, gbq, ci, mci, or uci."
    )