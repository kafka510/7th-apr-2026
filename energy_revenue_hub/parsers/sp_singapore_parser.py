"""
SP Group Singapore Clean Invoice Parser
Stable deterministic parser for Energy Revenue Hub
"""

import re
from datetime import datetime
from typing import Dict, Optional


# -------------------------------------------------------
# UTILITIES
# -------------------------------------------------------

def parse_number(v):

    if v is None:
        return None

    try:
        v = str(v)
        # Fix OCR typo: Replace comma next to 0 or O with a decimal point 
        # (e.g. "0,1140" -> "0.1140")
        v = re.sub(r'\b([0Oo]),(\d+)\b', r'\g<1>.\g<2>', v)
        # Fix double-decimal OCR artifact: "18,887.,82" -> "18,887.82"
        # EasyOCR sometimes reads the thousands separator period as both ',' and '.'
        v = re.sub(r',\.(\d)', r'.\1', v)   # e.g. "887.,82" -> "887.82"
        v = re.sub(r'\.,(\d)', r'.\1', v)   # e.g. "887.,82" -> "887.82" (alt order)
        v = v.replace(",", "")
        v = v.replace("$", "")
        v = v.replace("S", "")   # OCR artifact e.g. S2,520.21
        v = v.replace("kWh", "")
        return float(v.strip())
    except:
        return None


def parse_date(v):

    formats = [
        "%d %B %Y",
        "%d %b %Y",
        "%d/%m/%Y",
        "%d-%m-%Y"
    ]

    for f in formats:
        try:
            return datetime.strptime(v.strip(), f).strftime("%Y-%m-%d")
        except:
            pass

    return None


# -------------------------------------------------------
# BASIC FIELD EXTRACTION
# -------------------------------------------------------

def extract_account(text):

    m = re.search(r"Account\s*(?:No)?\.?\s*[:\-]?\s*\n?\s*(\d{7,})", text, re.I)

    if m:
        return m.group(1)

    return None


def extract_invoice_number(text):

    m = re.search(r"Invoice\s*(?:No)?\.?\s*[:\-]?\s*\n?\s*(\d{7,})", text, re.I)

    if m:
        return m.group(1)
        
    # Fallback for text-only extracts where the "Invoice No" label is missing
    # but the 20-digit SP barcode number is present at the bottom
    m_barcode = re.search(r"\b\d{3}-\d{6}-\d{5}-\d{4}\b", text)
    if m_barcode:
        return m_barcode.group(0).replace("-", "")

    return None


MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

def _get_month_idx(m_str):
    if not m_str: return None
    clean = m_str.lower().strip()[:3]
    if clean in MONTHS:
        return MONTHS.index(clean) + 1
    # Check for typos like JNov, lJul
    if len(m_str) > 3 and m_str.lower().strip()[1:4] in MONTHS:
        return MONTHS.index(m_str.lower().strip()[1:4]) + 1
    return None

def _parse_abv_billing_dates(text):
    """
    Parse the 3-column billing table in ABV/SP scanned invoices:
        [Billing Period] [Bill Date] [Account Type] [Deposit]
        start_date       end_date    bill_date       Non Domestic

    OCR often drops month names from one or more of the 3 dates, producing
    mixed patterns like:
        "26 2024 24 2024 26 May 2024"  (first 2 missing month)
        "25 2024 23 Feb 2024 28 Feb 2024"  (start missing month)
        "24 Feb 2023 24 Mar 2023 26 2023"  (bill date missing month)

    Returns (start_str, end_str, bill_str) as "YYYY-MM-DD", or (None,None,None).
    """
    header_m = re.search(
        r"Bil+(?:l?ing)?\s+Per?[il]od\s+Bil+\s+(?:D[ai]te?|Dat)",
        text, re.I
    )
    if not header_m:
        return None, None, None

    window = text[header_m.end(): header_m.end() + 200]

    # Step 1: find complete dates DD MMM YYYY, record their span
    complete = []  # (pos, datetime, end_pos)
    for m in re.finditer(r"\b(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})\b", window, re.I):
        try:
            dt = datetime.strptime(
                f"{int(m.group(1)):02d} {m.group(2)[:3].capitalize()} {m.group(3)}", "%d %b %Y"
            )
            complete.append((m.start(), dt, m.end()))
        except Exception:
            pass

    # Step 2: find partial dates DD YYYY not overlapping complete dates
    complete_spans = set()
    for s, _, e in complete:
        complete_spans.update(range(s, e))

    partial = []  # (pos, day_int, year_int)
    for m in re.finditer(r"\b(\d{1,2})\s+(\d{4})\b", window):
        if any(i in complete_spans for i in range(m.start(), m.end())):
            continue
        day, year = int(m.group(1)), int(m.group(2))
        if 1 <= day <= 31 and 2000 <= year <= 2035:
            partial.append((m.start(), day, year))

    # Step 3: merge and sort by position
    tokens = []  # (pos, 'C'|'P', value)
    for pos, dt, _ in complete:
        tokens.append((pos, 'C', dt))
    for pos, day, year in partial:
        tokens.append((pos, 'P', (day, year)))
    tokens.sort(key=lambda x: x[0])

    if len(tokens) < 3:
        return None, None, None

    t1, t2, t3 = tokens[0], tokens[1], tokens[2]

    # Step 4: infer months for partial tokens.
    # Anchor: use the last complete date we see among the 3 tokens.
    def _to_dt(tok, ref_dt):
        _, kind, val = tok
        if kind == 'C':
            return val
        day, year = val
        if ref_dt is None:
            return None
        try:
            return ref_dt.replace(day=day, year=year)
        except Exception:
            return None

    # Find anchor = last complete token among first 3
    ref = None
    for tok in (t3, t2, t1):
        if tok[1] == 'C':
            ref = tok[2]
            break
    if ref is None:
        return None, None, None

    end_dt = _to_dt(t2, ref)
    bill_dt = _to_dt(t3, end_dt or ref)

    # For start: use end_dt as ref, then roll back month if start_day > end_day
    start_dt = _to_dt(t1, end_dt or ref)
    if start_dt and end_dt and start_dt.day > end_dt.day:
        m_idx = start_dt.month - 1 or 12
        y = start_dt.year - (1 if start_dt.month == 1 else 0)
        try:
            start_dt = start_dt.replace(month=m_idx, year=y)
        except Exception:
            pass

    fmt = "%Y-%m-%d"
    return (
        start_dt.strftime(fmt) if start_dt else None,
        end_dt.strftime(fmt) if end_dt else None,
        bill_dt.strftime(fmt) if bill_dt else None,
    )


def extract_invoice_date(text):
    # print(f"[DEBUG extract_invoice_date] text[:300]={repr((text or '')[:300])}")
    # Try fully formed "Dated 08 Aug 2025" or "Bill Dated 1I Nov 2024" or "Dated_JNov 2024"
    m = re.search(
        r"dated[\s_]+([0-9IlO]{1,2})?[\s_]*([A-Za-z]{3,})[\s_]+(\d{4})",
        text,
        re.I
    )
    if m:
        day_str = m.group(1)
        month_str = m.group(2)
        year_str = m.group(3)
        
        # fix day typos
        if day_str:
            day_str = day_str.replace("I", "1").replace("l", "1").replace("O", "0")
        else:
            day_str = "01" # fallback if missing
            
        # fix month typo like 'JNov' -> 'Nov'
        if len(month_str) > 3 and month_str[0] in ['J', 'l', '1', 'I'] and month_str[1:] in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']:
            month_str = month_str[1:]
            
        try:
            dt_str = f"{day_str} {month_str[:3]} {year_str}"
            dt = datetime.strptime(dt_str, "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except:
             pass
    
    # Try tabular triplet: "25 Sep 2023 25 Oct 2023 30 Oct 2023" (Start, End, Bill Date)
    # Handles optional dash separator: "25 Mar 2023 - 24 Apr 2023 25 Apr 2023" (ABV invoices)
    m_triplet = re.search(
        r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*[-\u2013]?\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})",
        text,
        re.I
    )
    if m_triplet:
        bill_day, bill_month, bill_year = m_triplet.group(7), m_triplet.group(8), m_triplet.group(9)
        try:
            dt = datetime.strptime(f"{bill_day} {bill_month[:3]} {bill_year}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except:
            pass

    # ABV/SP billing table: handles cases where OCR drops month names from some dates
    # e.g. "26 2024 24 2024 26 May 2024" or "25 2024 23 Feb 2024 28 Feb 2024" etc.
    _, _, abv_bill = _parse_abv_billing_dates(text)
    if abv_bill:
        return abv_bill

    m2 = re.search(r"(?:[A-Za-z]+\s+\d{2,4}\s+)?Electricity\s+Bill\s+Dated[\s_]+([0-9IlO]{1,2})[\s_]+(\d{4})", text, re.I)
    if m2:
        day_str = m2.group(1).replace("I", "1").replace("l", "1").replace("O", "0")
        day = day_str.zfill(2)
        year = m2.group(2)
        bp_start, bp_end = extract_billing_period(text)
        if bp_end:
            return f"{year}-{bp_end[5:7]}-{day}"

    # New: handle "Bill Date" blocks without the word "Dated", e.g.
    # "Billing Period Bill Date Account Type Deposit 26 2024 24 2024 26 May 2024"
    m3 = re.search(
        r"Bill\s+Date[^\d]{0,20}([0-9IlO]{1,2})\s+([A-Za-z]{3,})\s+(\d{4})",
        text,
        re.I,
    )
    if m3:
        day_str = m3.group(1).replace("I", "1").replace("l", "1").replace("O", "0")
        month_str = m3.group(2)
        year_str = m3.group(3)
        try:
            dt = datetime.strptime(f"{day_str} {month_str[:3]} {year_str}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    # Additional: handle numeric Bill Date like "Bill Date 10-06-2025" or "Bill Date 10 06 2025"
    m4 = re.search(
        r"Bill\s+Date[^\d]{0,20}([0-9IlO]{1,2})[^\dA-Za-z]+([0-9IlO]{1,2})[^\dA-Za-z]+(\d{2,4})",
        text,
        re.I,
    )
    if m4:
        d = m4.group(1).replace("I", "1").replace("l", "1").replace("O", "0")
        m_ = m4.group(2).replace("I", "1").replace("l", "1").replace("O", "0")
        y = m4.group(3)
        # Normalise year to 4 digits if needed
        if len(y) == 2:
            y = "20" + y
        dt_str = f"{d.zfill(2)}-{m_.zfill(2)}-{y}"
        parsed = parse_date(dt_str)
        if parsed:
            return parsed

    # OCR truncation fallback: EasyOCR sometimes splits "Bill Dated" across lines,
    # resulting in "-ted DD MMM YYYY" patterns (the "Da" prefix is on the previous line).
    # Also handles "ted DD MMM YYYY" or "ated DD MMM YYYY" variants.
    m5 = re.search(
        r"(?:^|[\s\-])[Dd]?a?ted\s+([0-9IlO]{1,2})\s+([A-Za-z]{3})\s+(\d{4})",
        text,
        re.I | re.MULTILINE
    )
    if m5:
        day_str = m5.group(1).replace("I", "1").replace("l", "1").replace("O", "0")
        month_str = m5.group(2)
        year_str = m5.group(3)
        try:
            dt = datetime.strptime(f"{day_str} {month_str[:3]} {year_str}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    # Last resort: look for date on a line that contains "Electricity Bill"
    # OCR format: "MMM YY Electricity Bill Dated 31 Jan 2025" -- already handled by m above.
    # Fallback for "Electricity Bill" followed by a date anywhere on the same line:
    m6 = re.search(
        r"(?:Electricity\s+Bill|Tax\s+Invoice)[^\n]{0,60}(\d{1,2})\s+([A-Za-z]{3,})\s+(20\d{2})",
        text,
        re.I
    )
    if m6:
        day_str = m6.group(1)
        month_str = m6.group(2)
        year_str = m6.group(3)
        try:
            dt = datetime.strptime(f"{day_str} {month_str[:3]} {year_str}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    
    return None


def extract_billing_period(text):
    """
    Extract date range like '01 Jan 2025 to 31 Jan 2025' from text.
    Returns (start_date_str, end_date_str).
    """
    # Look for the exact format first (e.g. "01 Jan 2025 to 31 Jan 2025")
    m = re.search(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*t[o0]\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        text,
        re.I
    )
    if m:
        start_dt = parse_date(f"{m.group(1)} {m.group(2)} {m.group(3)}")
        end_dt = parse_date(f"{m.group(4)} {m.group(5)} {m.group(6)}")
        if start_dt and end_dt:
            return start_dt, end_dt

    # Try tabular triplet (pure-text OR ABV layout): "25 Sep 2023 25 Oct 2023 30 Oct 2023"
    # Handles optional dash separator: "25 Mar 2023 - 24 Apr 2023 25 Apr 2023"
    m_triplet = re.search(
        r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*[-\u2013]?\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})",
        text,
        re.I
    )
    if m_triplet:
        s_day, s_month, s_year = m_triplet.group(1), m_triplet.group(2), m_triplet.group(3)
        e_day, e_month, e_year = m_triplet.group(4), m_triplet.group(5), m_triplet.group(6)
        start_dt = parse_date(f"{s_day} {s_month[:3]} {s_year}")
        end_dt = parse_date(f"{e_day} {e_month[:3]} {e_year}")
        if start_dt and end_dt:
            return start_dt, end_dt

    # Fallback: OCR chopped out spaces, missed month names completely 
    # e.g "25 2024t0 24 2024" or "25 Jul 2024 t0 24 _ 2024"
    m2 = re.search(
        r"(\d{1,2})\s+(?:([A-Za-z_]+)\s+)?(\d{4})[\s_]*t[o0][\s_]*(\d{1,2})\s+(?:([A-Za-z_]+)\s+)?(\d{4})",
        text,
        re.I
    )
    if m2:
        sd, sm, sy, ed, em, ey = m2.groups()
        sd, ed = int(sd), int(ed)
        
        idx_s = _get_month_idx(sm)
        idx_e = _get_month_idx(em)
        
        # If both missing, guess from Invoice Date regex dynamically
        if not idx_s and not idx_e:
            m3 = re.search(r"dated[\s_]+(?:[0-9IlO]{1,2})?[\s_]*([A-Za-z]{3,})[\s_]+(?:\d{4})", text, re.I)
            if m3:
                idx_inv = _get_month_idx(m3.group(1))
                if idx_inv:
                    idx_e = idx_inv - 1 if idx_inv > 1 else 12
                    
        # Guess missing month based on the other mathematically
        if idx_s and not idx_e:
            idx_e = idx_s + 1 if ed < sd else idx_s
            if idx_e > 12: idx_e = 1
        elif idx_e and not idx_s:
            idx_s = idx_e - 1 if ed < sd else idx_e
            if idx_s < 1: idx_s = 12
            
        if idx_s and idx_e:
            start_str = f"{sy}-{idx_s:02d}-{sd:02d}"
            end_str = f"{ey}-{idx_e:02d}-{ed:02d}"
            return start_str, end_str

    # ABV layout: months missing from period line, only in Bill Date column.
    # Examples:
    #   "Billing Period Bill Date Account Type Deposit 26 2024 24 2024 26 May 2024"
    #   "Period Bill Date Account Type Deposit 24 Feb 2023 24 Mar 2023 26 Mar 2023"
    # Also handles OCR-noisy labels like "Bllling Perlod BIII Date".
    # Strategy: find any occurrence of 3 dates near a 'Bill Date'/'Period' keyword.

    # Pattern A: period_start and period_end have full month names
    # e.g. "Period Bill Date ... 24 Feb 2023 24 Mar 2023 26 Mar 2023"
    # Use the triplet regex which already handles this above — so if we reach here
    # neither triplet nor 'to' format was found.  Try the 'Billing Period' label anchor
    # with OCR-noise tolerance ('Bil+' covers 'Bllling', 'Billing', 'Bill'):
    m_labeled = re.search(
        r"(?:Bil+(?:l?ing|l)?\s+Per?[il]od|Period)\s+Bil+\s+Date[^\n]{0,80}?"
        r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})\s*[-\u2013]?\s*"
        r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})\s*"
        r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})",
        text,
        re.I | re.S,
    )
    if m_labeled:
        s_day, s_month, s_year = m_labeled.group(1), m_labeled.group(2), m_labeled.group(3)
        e_day, e_month, e_year = m_labeled.group(4), m_labeled.group(5), m_labeled.group(6)
        start_dt = parse_date(f"{s_day} {s_month[:3]} {s_year}")
        end_dt = parse_date(f"{e_day} {e_month[:3]} {e_year}")
        if start_dt and end_dt:
            return start_dt, end_dt

    # Pattern B: only day+year in period columns, month in the Bill Date column.
    # "Billing Period Bill Date Account Type Deposit 26 2024 24 2024 26 May 2024"
    m_dayonly = re.search(
        r"(?:Bil+(?:l?ing|l)?\s+Per?[il]od|Period).*?([0-9]{1,2})\s+([0-9]{4})\s+([0-9]{1,2})\s+([0-9]{4})\s+([0-9]{1,2})\s+([A-Za-z]{3,})\s+([0-9]{4})",
        text,
        re.I | re.S,
    )
    if m_dayonly:
        s_day = int(m_dayonly.group(1))
        s_year = int(m_dayonly.group(2))
        e_day = int(m_dayonly.group(3))
        e_year = int(m_dayonly.group(4))
        bill_day = int(m_dayonly.group(5))
        bill_month_str = m_dayonly.group(6)
        bill_year = int(m_dayonly.group(7))

        try:
            bill_dt = datetime.strptime(f"{bill_day} {bill_month_str[:3]} {bill_year}", "%d %b %Y")
            end_month = bill_dt.month
            end_year = bill_dt.year

            # If start day > end day, assume start is previous month
            if s_day > e_day:
                start_month = end_month - 1
                start_year = end_year
                if start_month < 1:
                    start_month = 12
                    start_year -= 1
            else:
                start_month = end_month
                start_year = end_year

            start_str = f"{start_year:04d}-{start_month:02d}-{s_day:02d}"
            end_str = f"{end_year:04d}-{end_month:02d}-{e_day:02d}"
            return start_str, end_str
        except Exception:
            pass

    return None, None


# -------------------------------------------------------
# TABLE PARSING
# -------------------------------------------------------

def extract_export_from_tables(tables):

    if not tables:
        return None, None

    for table in tables:

        for row in table:

            if not row:
                continue

            row_text = " ".join(str(c) for c in row if c).lower()

            if "export of electricity" not in row_text:
                continue

            usage = None
            amount = None

            for cell in row:
            
                val = parse_number(cell)
            
                if val is None:
                    continue

                # In multi-line export tables (two export rows in one block),
                # we want the *first* export row, which is always the lower
                # kWh usage figure. Use a lower kWh threshold and lock onto
                # the first valid (usage, amount) pair we see.
                if usage is None and val > 1000:
                    usage = val
                    continue
            
                if usage is not None and amount is None and 50 < val < 10000:
                    amount = val
                    # We found the first (usage, amount) pair – stop scanning
                    # this row so we don't accidentally pick the second row.
                    break
            
            if usage is not None and amount is not None:
                return usage, amount

    return None, None


def extract_recurring_from_tables(tables):

    if not tables:
        return None

    for table in tables:

        for row in table:

            if not row:
                continue

            row_text = " ".join(str(c) for c in row if c).lower()

            if "current charges exclusive of gst" not in row_text:
                continue

            for cell in row:

                val = parse_number(cell)

                if val and 5 < val < 500:
                    return val

    return None


# -------------------------------------------------------
# TEXT FALLBACK (LABEL-ANCHORED)
# -------------------------------------------------------

def detect_export_from_text(text):
    """
    Robust export block extraction for SP invoices.
    Uses mathematical invariant search (Usage * Rate = Amount) when OCR layout 
    is destroyed, avoiding brittle text-order guessing.
    """
    t = text or ""
    
    # 1. Look for the kWh measurement value (the number directly before a standalone kWh unit)
    #    Strategy: find ALL occurrences of "number kWh" in the export context, pick the one
    #    that is plausibly an energy reading (>100).
    kwh = None

    # Step 1a: Look for a number directly adjacent to "kWh" (unit marker) in the export block.
    # This handles formats like "18,887.,82 kWh" and "22,113.41 kWh" and "22,113.41kWh"
    # IMPORTANT: use [.,]+ (one or more separators) to handle OCR double-decimal ".,82" artifacts.
    # parse_number() then normalizes "18,887.,82" -> 18887.82
    for kwh_match in re.finditer(r"([\d,]+(?:[.,]+\d+)*)\s*kwh", t, re.I):
        candidate = parse_number(kwh_match.group(1))
        if candidate and candidate > 100:
            # Verify this kWh is in the export context (not just any kWh reading from the page)
            # by checking if "export" appears before it in the text (within a reasonable window)
            start = max(0, kwh_match.start() - 200)
            context = t[start:kwh_match.start()].lower()
            if "export" in context:
                kwh = candidate
                break
    
    # Step 1b: If export context search didn't find it, take the first plausible kWh reading
    if not kwh:
        for kwh_match in re.finditer(r"([\d,]+(?:[.,]+\d+)*)\s*kwh", t, re.I):
            candidate = parse_number(kwh_match.group(1))
            if candidate and candidate > 1000:
                kwh = candidate
                break

    amounts = []
    rates = []
    
    # Find all numeric-ish blobs (including OCR typos like 0,1140)
    for val in re.findall(r"([\d,]+[\.,]\d+)", t):
        num = parse_number(val)
        if not num: continue
        if 0.01 <= num <= 0.6:
            rates.append(num)
        elif num > 10:
            amounts.append(num)
            
    rates = list(set(rates))
    amounts = sorted(list(set(amounts)), reverse=True)
    
    detected_rate = None

    # 2. If Usage is known, find confirming Amount using exact rate match first
    if kwh:
        best_diff = 999
        best_amount = None
        best_rate = None

        for a in amounts:
            implied_rate = a / kwh
            if 0.04 <= implied_rate <= 0.40:
                for r in rates:
                    if abs(implied_rate - r) < 0.005:
                        diff = abs(implied_rate - r)
                        if diff < best_diff:
                            best_diff = diff
                            best_amount = a
                            best_rate = r
        if best_amount is not None:
            return kwh, best_amount, best_rate

        # 2b. If known Usage but NO exact rate matched, try again with a tighter normal band and pick the SMALLEST valid amount? 
        # Actually, let's just pick the smallest amount that fits to avoid matching grand totals!
        for a in reversed(amounts): # sorted ascending now
            rate_implied = a / kwh
            if 0.04 <= rate_implied <= 0.50: # Expanded price band
                return kwh, a, rate_implied

    # 3. If no explicit Usage found (or couldn't match amount), search for 
    #    the triplet invariant: Cost / Usage = Rate
    best_diff = 999
    best_pair = (None, None, None)
    
    for usage_cand in amounts:
        for cost_cand in amounts:
            if usage_cand <= cost_cand:
                continue # Usage is typically larger than cost (since rate < 1)
            
            implied_rate = cost_cand / usage_cand
            if not (0.04 <= implied_rate <= 0.40):
                continue
                
            for r in rates:
                # Math tolerance for rounding errors
                if abs(implied_rate - r) < 0.005: 
                    diff = abs(implied_rate - r)
                    if diff < best_diff:
                        best_diff = diff
                        best_pair = (usage_cand, cost_cand, r)
                        
    if best_pair[0] is not None:
        return best_pair
        
    return kwh, None, detected_rate


def detect_recurring_from_text(text):
    """
    Detect recurring charges from the 'Current Charges Exclusive of GST' block.
    Uses a label-anchored regex so we don't confuse IGS line items with the
    total recurring amount.
    """
    m = re.search(
        r"Current\s+Charges\s+Exclusive\s+(?:of|@f)\s+GST.*?([\d,]+\.\d{2})",
        text or "",
        re.I | re.S,
    )
    if not m:
        return None
    return parse_number(m.group(1))


def detect_current_charges_excl_gst_from_text(text):
    """Alias field for explicit UtilityInvoice column persistence."""
    return detect_recurring_from_text(text)


# -------------------------------------------------------
# VALIDATION
# -------------------------------------------------------

def validate(result):

    kwh = result.get("export_energy_kwh")
    cost = result.get("export_energy_cost")

    if kwh and cost:

        price = cost / kwh

        # SP export price band ranges; keep values but flag obviously
        # suspicious prices instead of blanking them out. Some OCR
        # variants can drift slightly yet still be usable.
        if not (0.03 < price < 0.80):
            warnings = result.setdefault("warnings", [])
            warnings.append(f"suspicious_export_price:{price:.6f}")

    return result


def calculate_confidence(result, is_type_2=False):
    """Return (score 0-100, level 'HIGH'|'MEDIUM'|'LOW') based on filled fields."""
    score = 0
    if result.get("invoice_number"):
        score += 15
    if result.get("invoice_date"):
        score += 15
    if result.get("account_number"):
        score += 10
    if result.get("export_energy_kwh"):
        score += 25
    if result.get("export_energy_cost"):
        score += 25
        
    # For Type 2 invoices, recurring charges are not applicable, 
    # so we treat it as satisfied. For Type 1, we require the parsed value.
    if is_type_2 or result.get("recurring_charges") is not None:
        score += 10
        
    score = max(0, min(score, 100))
    level = "HIGH" if score >= 80 else "MEDIUM" if score >= 60 else "LOW"
    return score, level


# -------------------------------------------------------
# MAIN PARSER
# -------------------------------------------------------

class SPSingaporeParser:

    vendor_key = "SP_SINGAPORE"

    def parse(self, text=None, words=None, tables=None, pdf_path=None, **kwargs):
        """
        Coordinate-aware parser for SP Singapore invoices.

        Uses OCR word coordinates (words) to extract stable values from fixed
        layout rows, with light regex support for date / period. This avoids
        brittle OCR text-order guessing.
        """

        if not words and not text:
            pass
            
        # Debug snapshot (kept to help troubleshooting)
        # print("\n================ DEBUG START ================")
        # print("TEXT LENGTH:", len(text) if text else 0)
        # if tables:
        #     print("\nTABLES FOUND:", len(tables))
        #     for i, t in enumerate(tables):
        #         print(f"\n--- TABLE {i+1} ---")
        #         for r in t:
        #             print(r)
        # else:
        #     print("\nNO TABLES DETECTED")
        # if words:
        #     print("\nWORDS SAMPLE:", words[:20])
        # else:
        #     print("\nNO WORDS DETECTED")
        # print("================ DEBUG END =================\n")
        # Base result for Energy Revenue Hub
        result: Dict[str, Optional[float]] = {
            "site_address": None,
            "account_number": extract_account(text) if text else None,
            "invoice_number": extract_invoice_number(text) if text else None,
            "invoice_date": extract_invoice_date(text) if text else None,
            "period_start": None,
            "period_end": None,
            "export_energy_kwh": None,
            "export_energy_cost": None,
            "unit_rate": None,
            "recurring_charges": None,
            "current_charges_excl_gst": None,
        }

        if text:
            start, end = extract_billing_period(text)
            if start and end:
                result["period_start"] = start
                result["period_end"] = end

        if not words:
            # If we have no coordinates at all, fall back to the text-only
            # export detection as a last resort, but still compute confidence.
            if text:
                kwh_txt, cost_txt, unit_rate_txt = detect_export_from_text(text)
                if kwh_txt and cost_txt:
                    result["export_energy_kwh"] = round(kwh_txt, 2)
                    result["export_energy_cost"] = round(cost_txt, 2)
                    if unit_rate_txt:
                        result["unit_rate"] = round(unit_rate_txt, 4)
                    rec = detect_recurring_from_text(text)
                    if rec:
                        result["recurring_charges"] = rec
                        result["current_charges_excl_gst"] = rec
                    result = validate(result)

                    # Confidence logic:
                    # Type 1 invoices: invoice_number, invoice_date, account_number,
                    # export_energy_kwh, export_energy_cost, recurring_charges all present
                    # and validated -> 100%.
                    # Type 2 invoices: same, but recurring_charges can be missing.
                    is_type_2 = "recurring charges" not in text.lower()
                    score, level = calculate_confidence(result, is_type_2=is_type_2)
                    result["confidence_score"] = score
                    result["confidence_flag"] = level
            return result

        # ----------------------------
        # Helper functions (coordinates)
        # ----------------------------

        def find_word(keyword: str):
            for w in words:
                if keyword.lower() in str(w[4]).lower():
                    return w
            return None

        def words_near_y(y: float, tol: float = 25.0):
            row = []
            for w in words:
                if abs(w[1] - y) < tol:
                    row.append(w[4])
            return row

        def words_right_of(x: float, y: float, tol_y: float = 20.0):
            row = []
            for w in words:
                if abs(w[1] - y) < tol_y and w[0] > x:
                    row.append(w[4])
            return row

        # ----------------------------
        # Invoice / Account (by layout)
        # ----------------------------

        label = find_word("Invoice")
        if label:
            vals = words_right_of(label[2], label[1])
            for v in vals:
                if re.match(r"\d{8,}", str(v)):
                    result["invoice_number"] = str(v)
                    break

        label = find_word("Account")
        if label:
            vals = words_right_of(label[2], label[1])
            for v in vals:
                if re.match(r"\d{8,}", str(v)):
                    result["account_number"] = str(v)
                    break

        # ----------------------------
        # Invoice date (text-based)
        # ----------------------------

        if text:
            m = re.search(r"Bill Dated\s*(\d{1,2}\s+\w+\s+\d{4})", text, re.I)
            if m:
                try:
                    dt = datetime.strptime(m.group(1), "%d %b %Y")
                    result["invoice_date"] = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

        # ----------------------------
        # Export row (by Y coordinate)
        # ----------------------------

        label = find_word("Export")
        if label:
            row = words_near_y(label[1], tol=15.0)
            usage = None
            rate = None
            amounts = []

            for r in row:
                txt = str(r)
                val = parse_number(txt)
                if val is None:
                    continue

                if "kwh" in txt.lower() and val > 1000:
                    usage = val
                elif 0.05 < val < 0.40:
                    rate = val
                elif val > 100:
                    amounts.append(val)

            amount = None

            # Attempt to derive exact amount using Usage * Rate math to handle OCR layout bleed
            if usage and rate:
                expected = usage * rate
                best_diff = 999999
                for a in amounts:
                    if abs(a - expected) < best_diff and a != usage:
                        best_diff = abs(a - expected)
                        amount = a
            
            # Fallback if math didn't trigger
            if amount is None and amounts:
                cands = [a for a in amounts if a != usage]
                if cands:
                    amount = cands[-1]

            # Fallback: find first big kWh anywhere on page if row missed usage
            if usage is None:
                for w in words:
                    txt = str(w[4])
                    if "kwh" in txt.lower():
                        val = parse_number(txt)
                        if val and val > 1000:
                            usage = val
                            break

            # As final safety, when kWh is still missing but rate/amount present,
            # derive kWh from amount / rate.
            if usage is None and rate and amount:
                usage = round(amount / rate, 2)

            result["export_energy_kwh"] = usage
            result["export_energy_cost"] = amount
            result["unit_rate"] = rate
        
        # Cross-check and self-heal with text block logic (mathematical invariant fallback)
        if text:
            kwh_txt, cost_txt, unit_rate_txt = detect_export_from_text(text)
            if kwh_txt and cost_txt:
                cur_kwh = result.get("export_energy_kwh")
                cur_cost = result.get("export_energy_cost")
                
                # Replace if coordinate extraction completely missed or got wild numbers
                if not cur_cost or not cur_kwh:
                    result["export_energy_kwh"] = round(kwh_txt, 2)
                    result["export_energy_cost"] = round(cost_txt, 2)
                    if unit_rate_txt:
                        result["unit_rate"] = round(unit_rate_txt, 4)
                else:
                    implied_rate = cur_cost / cur_kwh
                    if not (0.05 <= implied_rate <= 0.40):
                        result["export_energy_kwh"] = round(kwh_txt, 2)
                        result["export_energy_cost"] = round(cost_txt, 2)
                        if unit_rate_txt:
                            result["unit_rate"] = round(unit_rate_txt, 4)

        # ----------------------------
        # Recurring charges (layout + text)
        # ----------------------------

        if result.get("recurring_charges") is None:
            for w in words:
                txt = str(w[4])
                if "Current Charges Exclusive" in txt:
                    row = words_near_y(w[1])
                    for r in row:
                        val = parse_number(str(r))
                        if val and 5 < val < 500:
                            result["recurring_charges"] = val
                            result["current_charges_excl_gst"] = val
                            break
                    if result.get("recurring_charges") is not None:
                        break

        # Text fallback if layout-based recurring failed
        if result.get("recurring_charges") is None and text:
            rec = detect_recurring_from_text(text)
            if rec:
                result["recurring_charges"] = rec
                result["current_charges_excl_gst"] = rec

        if result.get("current_charges_excl_gst") is None and text:
            cc = detect_current_charges_excl_gst_from_text(text)
            if cc:
                result["current_charges_excl_gst"] = cc

        # Determine if it's type 2 (missing recurring charges section entirely)
        is_type_2 = False
        if text and "recurring charges" not in text.lower():
            is_type_2 = True

        # Final validation + confidence scoring
        result = validate(result)
        score, level = calculate_confidence(result, is_type_2=is_type_2)
        result["confidence_score"] = score
        result["confidence_flag"] = level

        return result