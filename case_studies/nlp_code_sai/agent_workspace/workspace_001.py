def filter_records(records: list, threshold: float) -> list:
    """Return a new list containing only the records whose ``score`` value is
    strictly greater than ``threshold``.

    Parameters
    ----------
    records: list
        A list of dictionaries. Each dictionary may or may not contain a
        ``'score'`` key. If the key is missing, the record is ignored.
    threshold: float
        The numeric threshold that a record's ``score`` must exceed.

    Returns
    -------
    list
        A list of the original record dictionaries that satisfy the condition,
        preserving their original order. The original ``records`` list is not
        modified.
    """
    # Use a list comprehension to filter while preserving order.
    # ``record.get('score')`` returns ``None`` if the key is missing; comparing
    # ``None`` with a float raises a TypeError, so we explicitly check for the
    # presence of the key and that the value is comparable.
    filtered = []
    for record in records:
        # Ensure the record is a dict and contains a numeric 'score'.
        if not isinstance(record, dict):
            continue
        if 'score' not in record:
            continue
        score = record['score']
        # Only consider int or float types for comparison.
        if isinstance(score, (int, float)) and score > threshold:
            filtered.append(record)
    return filtered
