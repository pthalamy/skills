# GEDCOM change log

File: `<input filename>` → `<output filename>` (GEDCOM <version>, <encoding>, <BOM/CRLF kept>)
Date: <YYYY-MM-DD>
Request: <one line restating what the user asked for>

## Validation

`validate_gedcom.py` before: <PASS/FAIL, n errors, n warnings>
`validate_gedcom.py` after: <PASS/FAIL, n errors, n warnings>
<Pre-existing findings left untouched, if any, and why.>

## Records added

| Xref | Type | Who / what | Evidence (source, page, QUAY) |
| ---- | ---- | ---------- | ----------------------------- |
| @I…@ | INDI | | |

## Records changed

| Xref | Field | Before | After | Evidence (source, page, QUAY) | Level |
| ---- | ----- | ------ | ----- | ----------------------------- | ----- |
| @I…@ | BIRT.DATE | ABT 1795 | 12 VEND 4 | @S3@ acte 34 vue 12, QUAY 3 | Documented |

Level is Documented, Corroborated or Hypothesis (see `references/evidence-and-gedcom.md`).

## Records removed or merged

| Xref removed | Merged into | Identity established by |
| ------------ | ----------- | ----------------------- |

## Conflicts and hypotheses left open

- **@I…@ <field>**: <the two values, which is currently canonical and why, the record that would decide it>.

## Not done

- <Anything requested that the evidence did not support, with the reason and the record that would be needed.>

## Notes for the user

- <Encoding, dialect or software-specific caveats; anything to verify on re-import.>
