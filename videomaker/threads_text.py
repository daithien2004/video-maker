"""Pillow text with a local emoji font fallback, sharing measurement and drawing."""
import re
import base64
import io
import math
from functools import lru_cache
from pathlib import Path

_BASE = r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2300-\u23FF]'
_PART = _BASE + r'[\uFE0E\uFE0F\U0001F3FB-\U0001F3FF]*'
_EMOJI = re.compile(_PART + r'(?:\u200D' + _PART + r')*|[0-9#*]\uFE0F?\u20E3')
_GLYPHS = {}


def prepare_emojis(texts):
    """Chromium shapes color/ZWJ/skin-tone sequences even without Pillow RAQM."""
    missing = {m.group() for text in texts for m in _EMOJI.finditer(text)} - _GLYPHS.keys()
    if not missing:
        return
    from PIL import Image
    from playwright.sync_api import sync_playwright
    from .paths import configure_browser_temp
    configure_browser_temp()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            glyphs = page.evaluate('''tokens => tokens.map(text => {
                const canvas = document.createElement('canvas');
                canvas.width = 600; canvas.height = 200;
                const ctx = canvas.getContext('2d');
                ctx.font = '128px "Segoe UI Emoji", sans-serif';
                ctx.textBaseline = 'alphabetic';
                const width = ctx.measureText(text).width;
                ctx.fillText(text, 8, 144);
                return {text, width, png: canvas.toDataURL('image/png').split(',')[1]};
            })''', sorted(missing))
            for glyph in glyphs:
                bitmap = Image.open(io.BytesIO(base64.b64decode(glyph['png']))).convert('RGBA')
                bounds = bitmap.getbbox()
                if bounds:
                    _GLYPHS[glyph['text']] = (bitmap.crop(bounds), glyph['width'], bounds[0] - 8, bounds[1] - 144)
        finally:
            browser.close()


def _glyph(run, font):
    from PIL import Image
    bitmap, width, left, top = _GLYPHS[run]
    scale = font.size / 128
    size = (max(1, round(bitmap.width * scale)), max(1, round(bitmap.height * scale)))
    return bitmap.resize(size, Image.Resampling.LANCZOS), width * scale, left * scale, top * scale


@lru_cache(maxsize=64)
def emoji_font(size):
    from PIL import ImageFont
    path = Path('C:/Windows/Fonts/seguiemj.ttf')
    return ImageFont.truetype(str(path), size) if path.is_file() else None


class EmojiDraw:
    def __init__(self, draw):
        self.draw = draw

    def __getattr__(self, name):
        return getattr(self.draw, name)

    def _runs(self, text, font):
        fallback = emoji_font(getattr(font, 'size', 32))
        if fallback is None:
            return [(text, font, False)]
        runs, end = [], 0
        for match in _EMOJI.finditer(text):
            if match.start() > end:
                runs.append((text[end:match.start()], font, False))
            runs.append((match.group(), fallback, True))
            end = match.end()
        if end < len(text):
            runs.append((text[end:], font, False))
        return runs

    def textlength(self, text, font):
        return sum(_glyph(run, f)[1] if emoji and run in _GLYPHS else self.draw.textlength(run, font=f)
                   for run, f, emoji in self._runs(text, font))

    def textbbox(self, xy, text, font):
        x, y = xy
        baseline = y + font.getmetrics()[0]
        boxes = []
        for run, f, emoji in self._runs(text, font):
            if emoji and run in _GLYPHS:
                bitmap, width, left, top = _glyph(run, f)
                boxes.append((x + left, baseline + top, x + left + bitmap.width, baseline + top + bitmap.height))
                x += width
            else:
                boxes.append(self.draw.textbbox((x, baseline), run, font=f, anchor='ls'))
                x += self.draw.textlength(run, font=f)
        return (math.floor(min(b[0] for b in boxes)), math.floor(min(b[1] for b in boxes)),
                math.ceil(max(b[2] for b in boxes)), math.ceil(max(b[3] for b in boxes))) if boxes else (*xy, *xy)

    def text(self, xy, text, font, fill):
        x, y = xy
        baseline = y + font.getmetrics()[0]
        for run, f, emoji in self._runs(text, font):
            if emoji and run in _GLYPHS:
                bitmap, width, left, top = _glyph(run, f)
                self.draw._image.paste(bitmap, (round(x + left), round(baseline + top)), bitmap)
                x += width
                continue
            self.draw.text((x, baseline), run, font=f, fill=fill,
                           anchor='ls', embedded_color=emoji)
            x += self.draw.textlength(run, font=f)
