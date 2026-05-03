"""
clean_logs.py — Strip LaTeX math notation and tidy up markdown artifacts
from debate JSON log files.

Usage:
    python clean_logs.py                      # clean all logs in-place
    python clean_logs.py --dry-run            # preview changes, no writes
    python clean_logs.py --dir path/to/logs   # custom log directory
    python clean_logs.py file1.json file2.json  # specific files
"""

import argparse
import json
import re
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"


def _clean_inline_math(match: re.Match) -> str:
    """
    Best-effort humanisation of an arbitrary $...$ block.
    Strips LaTeX commands and makes the expression readable as plain text.
    """
    inner = match.group(1)

    # llama.cpp / JSON encoding corruption: control chars appear where LaTeX had \X.
    # In JSON, \t=tab, \r=CR, \n=LF, \b=backspace, \f=form-feed are escape sequences.
    # If the JSON file was written without double-escaping the backslash, these get
    # decoded into control characters, eating the first letter of the LaTeX command.
    # e.g.  \text → chr(9)+ext   \rightarrow → chr(13)+ightarrow   \neg → chr(10)+eg
    # Restore: replace each control char with backslash + the letter it consumed.
    inner = inner.replace('\t', '\\t')   # \text, \tau, \theta, \times, \top …
    inner = inner.replace('\r', '\\r')   # \rightarrow, \rho, \rangle …
    inner = inner.replace('\n', '\\n')   # \neg, \nu, \nabla, \neq …
    inner = inner.replace('\b', '\\b')   # \beta, \big, \boldsymbol …
    inner = inner.replace('\f', '\\f')   # \forall, \frac, \phi …

    # Replace \text{X} → X
    inner = re.sub(r'\\text\{([^}]+)\}', r'\1', inner)

    # Replace subscript / superscript braces: _{X} → _X,  ^{X} → ^X
    inner = re.sub(r'_\{([^}]+)\}', r'_\1', inner)
    inner = re.sub(r'\^\{([^}]+)\}', r'^\1', inner)

    # Known symbol commands
    symbol_map = {
        # Arrows
        r'\\rightarrow': '→', r'\\leftarrow': '←',
        r'\\leftrightarrow': '↔', r'\\Rightarrow': '⇒',
        r'\\Leftarrow': '⇐', r'\\Leftrightarrow': '⇔',
        r'\\to': '→',
        # Comparison
        r'\\leq': '≤', r'\\geq': '≥', r'\\neq': '≠',
        r'\\approx': '≈', r'\\equiv': '≡',
        # Math
        r'\\times': '×', r'\\div': '÷', r'\\pm': '±',
        r'\\infty': '∞', r'\\cdot': '·',
        r'\\partial': '∂', r'\\nabla': '∇',
        r'\\sum': 'Σ', r'\\prod': 'Π', r'\\int': '∫',
        # Sets / logic
        r'\\in': '∈', r'\\notin': '∉',
        r'\\subset': '⊂', r'\\subseteq': '⊆',
        r'\\cup': '∪', r'\\cap': '∩',
        r'\\forall': '∀', r'\\exists': '∃',
        r'\\neg': '¬', r'\\land': '∧', r'\\lor': '∨',
        # Punctuation
        r'\\ldots': '…', r'\\dots': '…', r'\\cdots': '⋯',
        # Greek lowercase
        r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ',
        r'\\delta': 'δ', r'\\epsilon': 'ε', r'\\varepsilon': 'ε',
        r'\\zeta': 'ζ', r'\\eta': 'η', r'\\theta': 'θ',
        r'\\iota': 'ι', r'\\kappa': 'κ', r'\\lambda': 'λ',
        r'\\mu': 'μ', r'\\nu': 'ν', r'\\xi': 'ξ',
        r'\\pi': 'π', r'\\rho': 'ρ', r'\\sigma': 'σ',
        r'\\tau': 'τ', r'\\upsilon': 'υ', r'\\phi': 'φ',
        r'\\chi': 'χ', r'\\psi': 'ψ', r'\\omega': 'ω',
        # Greek uppercase
        r'\\Gamma': 'Γ', r'\\Delta': 'Δ', r'\\Theta': 'Θ',
        r'\\Lambda': 'Λ', r'\\Xi': 'Ξ', r'\\Pi': 'Π',
        r'\\Sigma': 'Σ', r'\\Phi': 'Φ', r'\\Psi': 'Ψ',
        r'\\Omega': 'Ω',
    }
    for cmd, sym in symbol_map.items():
        inner = re.sub(cmd, sym, inner)

    # Drop any remaining unknown \commands (e.g. \frac, \sqrt)
    inner = re.sub(r'\\[a-zA-Z]+', '', inner)

    # Clean up stray braces
    inner = inner.replace('{', '').replace('}', '')

    # Collapse multiple spaces
    inner = re.sub(r' {2,}', ' ', inner).strip()

    return inner


# ---------------------------------------------------------------------------
# Replacement rules — applied in order
# Each entry: (compiled_regex, replacement_string_or_callable)
# ---------------------------------------------------------------------------

RULES = [
    # --- LaTeX arrows & logic symbols ---
    (re.compile(r'\$\\rightarrow\$'),       '→'),
    (re.compile(r'\$\\leftarrow\$'),        '←'),
    (re.compile(r'\$\\leftrightarrow\$'),   '↔'),
    (re.compile(r'\$\\Rightarrow\$'),       '⇒'),
    (re.compile(r'\$\\Leftarrow\$'),        '⇐'),
    (re.compile(r'\$\\Leftrightarrow\$'),   '⇔'),
    (re.compile(r'\$\\to\$'),               '→'),

    # --- LaTeX comparison operators ---
    (re.compile(r'\$\\leq\$'),              '≤'),
    (re.compile(r'\$\\geq\$'),              '≥'),
    (re.compile(r'\$\\neq\$'),              '≠'),
    (re.compile(r'\$\\approx\$'),           '≈'),
    (re.compile(r'\$\\equiv\$'),            '≡'),
    (re.compile(r'\$\\lt\$'),               '<'),
    (re.compile(r'\$\\gt\$'),               '>'),

    # --- LaTeX set / logic symbols ---
    (re.compile(r'\$\\in\$'),               '∈'),
    (re.compile(r'\$\\notin\$'),            '∉'),
    (re.compile(r'\$\\subset\$'),           '⊂'),
    (re.compile(r'\$\\subseteq\$'),         '⊆'),
    (re.compile(r'\$\\cup\$'),              '∪'),
    (re.compile(r'\$\\cap\$'),              '∩'),
    (re.compile(r'\$\\forall\$'),           '∀'),
    (re.compile(r'\$\\exists\$'),           '∃'),
    (re.compile(r'\$\\neg\$'),              '¬'),
    (re.compile(r'\$\\land\$'),             '∧'),
    (re.compile(r'\$\\lor\$'),              '∨'),

    # --- LaTeX math symbols ---
    (re.compile(r'\$\\times\$'),            '×'),
    (re.compile(r'\$\\div\$'),              '÷'),
    (re.compile(r'\$\\pm\$'),               '±'),
    (re.compile(r'\$\\infty\$'),            '∞'),
    (re.compile(r'\$\\cdot\$'),             '·'),

    # --- LaTeX inline math blocks: $\text{...}$ → plain text ---
    (re.compile(r'\$\\text\{([^}]*)\}\$'),  r'\1'),

    # --- Subscript/superscript math expressions like $V_{\text{X}}$ ---
    # Converts $V_{\text{Life}}$ → V_Life, $A^{B}$ → A^B
    (re.compile(r'\$([A-Za-z]+)_\{\\text\{([^}]+)\}\}\$'),   r'\1_\2'),
    (re.compile(r'\$([A-Za-z]+)\^?\{\\text\{([^}]+)\}\}\$'),  r'\1^\2'),

    # --- Remaining bare $...$ math expressions ---
    # Try to make them readable by stripping the $ delimiters and LaTeX commands
    # e.g. $V_{\text{Life} | \text{Suffering}} = V_{\text{Life}} - E$
    (re.compile(r'\$([^$]+)\$'), _clean_inline_math),

    # --- LaTeX text formatting ---
    (re.compile(r'\\textbf\{([^}]+)\}'),    r'\1'),
    (re.compile(r'\\textit\{([^}]+)\}'),    r'\1'),
    (re.compile(r'\\emph\{([^}]+)\}'),      r'\1'),
    (re.compile(r'\\underline\{([^}]+)\}'), r'\1'),

    # --- Stray backslash-escaped chars that leak out of math blocks ---
    (re.compile(r'\\rightarrow'),  '→'),
    (re.compile(r'\\leftarrow'),   '←'),
    (re.compile(r'\\leq'),         '≤'),
    (re.compile(r'\\geq'),         '≥'),
    (re.compile(r'\\neq'),         '≠'),
    (re.compile(r'\\times'),       '×'),
    (re.compile(r'\\cdot'),        '·'),
    (re.compile(r'\\ldots'),       '…'),
    (re.compile(r'\\dots'),        '…'),

    # --- Markdown artifacts ---
    # Unescape escaped asterisks that sometimes appear literally
    (re.compile(r'\\\*'),          '*'),
]


def clean_text(text: str) -> str:
    """Apply all rules to a single string."""
    for pattern, replacement in RULES:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text


def clean_value(obj):
    """Recursively clean all string values in a JSON structure."""
    if isinstance(obj, str):
        return clean_text(obj)
    if isinstance(obj, list):
        return [clean_value(v) for v in obj]
    if isinstance(obj, dict):
        return {k: clean_value(v) for k, v in obj.items()}
    return obj


def process_file(path: Path, dry_run: bool) -> tuple[int, int]:
    """
    Clean one JSON file.
    Returns (chars_before, chars_after) for reporting.
    """
    raw = path.read_text(encoding='utf-8')
    data = json.loads(raw)

    cleaned_data = clean_value(data)
    cleaned_raw = json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    before = len(raw)
    after = len(cleaned_raw)

    if raw == cleaned_raw:
        print(f"  [skip]  {path.name}  (no changes)")
        return before, after

    if dry_run:
        # Show a few sample changes
        _show_diff_sample(raw, cleaned_raw, path.name)
    else:
        path.write_text(cleaned_raw, encoding='utf-8')
        delta = before - after
        print(f"  [done]  {path.name}  ({delta:+d} chars)")

    return before, after


def _show_diff_sample(before: str, after: str, name: str, max_samples: int = 5):
    """Print a handful of changed lines to illustrate what was cleaned."""
    before_lines = before.splitlines()
    after_lines  = after.splitlines()

    print(f"\n  [dry-run] {name}")
    shown = 0
    for i, (b, a) in enumerate(zip(before_lines, after_lines)):
        if b != a:
            print(f"    line {i+1}")
            print(f"      before: {b.strip()[:120]}")
            print(f"      after:  {a.strip()[:120]}")
            shown += 1
            if shown >= max_samples:
                remaining = sum(1 for x, y in zip(before_lines[i+1:], after_lines[i+1:]) if x != y)
                if remaining:
                    print(f"    ... and {remaining} more changed lines")
                break


def main():
    parser = argparse.ArgumentParser(description="Clean LaTeX artifacts from debate JSON logs.")
    parser.add_argument('files', nargs='*', help="Specific JSON files to clean (default: all in logs/)")
    parser.add_argument('--dir', default=str(LOG_DIR), help="Log directory (default: ./logs)")
    parser.add_argument('--dry-run', action='store_true', help="Preview changes without writing")
    args = parser.parse_args()

    log_dir = Path(args.dir)

    if args.files:
        targets = []
        for file_arg in args.files:
            candidate = Path(file_arg)
            if candidate.is_absolute():
                targets.append(candidate)
            else:
                targets.append(log_dir / candidate)
    else:
        targets = sorted(log_dir.glob("*.json"))

    if not targets:
        print("No JSON files found.")
        sys.exit(0)

    mode = "DRY RUN — no files will be modified" if args.dry_run else "Cleaning files in-place"
    print(f"{mode}\n")

    for path in targets:
        if not path.exists():
            print(f"  [error] not found: {path}")
            continue
        try:
            process_file(path, dry_run=args.dry_run)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [error] {path.name}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
