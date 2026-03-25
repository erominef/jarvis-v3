# tools/data.py — Data analysis for workspace files.
#
# Loads CSV or JSON from workspace/, runs pandas analysis, returns summary.


def data_analyze(path: str) -> str:
    """
    Load a CSV or JSON file from workspace/ and return a statistical summary.
    Includes: shape, numeric describe(), top value_counts for categorical columns,
    missing value counts.
    Output capped at 3000 chars.
    """
    raise NotImplementedError
