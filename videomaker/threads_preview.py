"""Read-only Threads card metadata for full-frame preview selection."""
from . import threads_shot as ts
from .comment_manager import chronological


def preview_items(source):
    items = [source.get('post') or {}] + chronological(source.get('comments') or [])
    images = {item.get('rel'): item.get('path') for item in source.get('images') or []}
    result = []
    for index, item in enumerate(items):
        image = item.get('image')
        if not image:
            continue
        context = ts.reply_context(source, image)
        kind = 'post' if index == 0 else 'reply' if (item.get('depth') or 1) >= 2 else 'comment'
        _handle, snippet = ts.parse_context(context)
        result.append({'image': image, 'path': images.get(image), 'kind': kind,
                       'handle': item.get('handle') or '', 'text': item.get('text') or '',
                       'context': context, 'parent_snippet': snippet, 'has_parent_context': bool(snippet)})
    return result
