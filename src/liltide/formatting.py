"""Presentation-neutral formatting shared by captions and transcript files."""


def timestamp(ms):
    hours, remainder = divmod(max(0, ms), 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"
