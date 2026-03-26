# tools/data.py — Data analysis for workspace files.
#
# Loads CSV or JSON from workspace/, runs pandas analysis, returns summary.
# Tool: data_analyze

from pathlib import Path

_WORKSPACE = (Path(__file__).parent.parent / "workspace").resolve()


def data_analyze(path: str) -> str:
    try:
        import pandas as pd
    except ImportError:
        return "pandas not installed — add 'pandas' to requirements.txt."

    clean = path.strip()
    if clean.startswith("workspace/"):
        clean = clean[len("workspace/"):]

    candidate = (_WORKSPACE / clean).resolve()
    try:
        candidate.relative_to(_WORKSPACE)
    except ValueError:
        return "Rejected: path is outside workspace/."

    if not candidate.exists():
        return f"File not found: workspace/{clean}"

    suffix = candidate.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(str(candidate))
        elif suffix == ".json":
            df = pd.read_json(str(candidate))
        else:
            return f"Unsupported file type: {suffix}. Supported: .csv, .json"
    except Exception as e:
        return f"Failed to load file: {e}"

    lines = [f"File: workspace/{clean} | Rows: {len(df)} | Columns: {len(df.columns)}"]
    lines.append(f"Columns: {', '.join(df.columns.tolist())}")
    lines.append("")

    # Numeric summary
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe().round(2)
        lines.append("=== Numeric Summary ===")
        lines.append(desc.to_string())
        lines.append("")

    # Categorical summary (top values)
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    if cat_cols:
        lines.append("=== Categorical Columns ===")
        for col in cat_cols[:5]:  # cap at 5 columns
            vc = df[col].value_counts().head(5)
            lines.append(f"{col}: {', '.join(f'{v}({c})' for v, c in vc.items())}")
        lines.append("")

    # Missing values
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        lines.append("=== Missing Values ===")
        for col, count in missing.items():
            lines.append(f"  {col}: {count} missing ({count/len(df)*100:.1f}%)")

    output = "\n".join(lines)
    if len(output) > 3000:
        output = output[:3000] + "\n[truncated]"
    return output
