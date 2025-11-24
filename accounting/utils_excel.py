import io
from django.core.exceptions import ValidationError
import pandas as pd
from datetime import datetime


REQUIRED_COLUMNS = ['date', 'reference', 'numeroEcriture', 'libelle', 'nature', 'account', 'accountName', 'debit', 'credit', 'calculatedAmount', 'percentage', 'lineNature']


def read_excel_file(uploaded_file):
    """Read an uploaded Excel file (InMemoryUploadedFile) and return a list of dict rows.

    Raises ValidationError on missing columns or empty sheet.
    """
    try:
        # read into pandas DataFrame
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception as e:
        raise ValidationError(f"Unable to read Excel file: {e}")

    if df is None or df.empty:
        raise ValidationError("Excel sheet is empty")

    # normalize column names to expected lowercase keys
    df.columns = [str(c).strip() for c in df.columns]
    lower_map = {c: c.strip() for c in df.columns}
    # try to map common variations
    col_map = {}
    for col in df.columns:
        key = col.strip()
        low = key.lower()
        col_map[low] = col

    missing = [c for c in REQUIRED_COLUMNS if c not in col_map]
    if missing:
        # attempt to match common alternates (e.g., accountNumber->account)
        # If still missing, raise
        raise ValidationError(f"Missing required columns: {', '.join(missing)}")

    # build rows
    rows = []
    for _, r in df.iterrows():
        row = {}
        for key in REQUIRED_COLUMNS:
            raw_col = col_map.get(key)
            val = r[raw_col] if raw_col in r.index else None
            row[key] = val

        # normalize date
        date_val = row['date']
        parsed_date = None
        if pd.isna(date_val):
            parsed_date = None
        else:
            # if numeric (Excel date serial), convert
            if isinstance(date_val, (int, float)):
                try:
                    parsed_date = datetime.fromordinal(datetime(1899,12,31).toordinal() + int(date_val))
                except Exception:
                    # fallback to pandas
                    parsed_date = pd.to_datetime(date_val, unit='d', origin='1899-12-30', errors='coerce')
            else:
                # use pandas to parse text dates
                parsed_date = pd.to_datetime(date_val, errors='coerce')

        if parsed_date is None or pd.isna(parsed_date):
            raise ValidationError(f"Invalid date value: {row['date']}")

        row['date'] = parsed_date.strftime('%Y-%m-%d')

        # numeric fields
        for nfield in ('debit', 'credit', 'calculatedAmount', 'percentage'):
            v = row.get(nfield)
            try:
                if pd.isna(v):
                    row[nfield] = 0
                else:
                    row[nfield] = float(v)
            except Exception:
                row[nfield] = 0

        # string fields cleanup
        for s in ('reference', 'numeroEcriture', 'libelle', 'nature', 'account', 'accountName', 'lineNature'):
            v = row.get(s)
            if pd.isna(v):
                row[s] = ''
            else:
                row[s] = str(v).strip()

        rows.append(row)

    return rows
