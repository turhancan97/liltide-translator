"""Visible escaping for untrusted fields in terminal/human-readable output."""


def safe_text(value: str) -> str:
    """Keep Unicode prose; escape controls before adding trusted layout text."""
    escapes = {'\n': r'\n', '\r': r'\r', '\t': r'\t'}
    result = []
    for char in value:
        code = ord(char)
        if code < 32 or 127 <= code <= 159:
            result.append(escapes.get(char, f'\\x{code:02x}'))
        elif code in (0x2028, 0x2029):
            result.append(f'\\u{code:04x}')
        else:
            result.append(char)
    return ''.join(result)
