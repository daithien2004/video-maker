"""Persisted scan preferences; excludes post URLs and login data."""
DEFAULTS = dict(top=20, mode='auto', ident='avatar', nested=True,
                reply_depth=1, reply_min_likes=10, reply_per_parent=2)


def clean_options(value):
    if not isinstance(value, dict):
        return None
    result = DEFAULTS.copy()
    for key, choices in {'mode': ('auto', 'shot', 'card'),
                         'ident': ('avatar', 'full', 'no-avatar', 'anon')}.items():
        if key in value:
            if value[key] not in choices:
                return None
            result[key] = value[key]
    if 'nested' in value:
        if not isinstance(value['nested'], bool):
            return None
        result['nested'] = value['nested']
    for key, low, high in [('top', 0, 500), ('reply_depth', 1, 4),
                           ('reply_min_likes', 0, 1_000_000_000), ('reply_per_parent', 0, 100)]:
        if key in value:
            number = value[key]
            if isinstance(number, bool) or not isinstance(number, int) or not low <= number <= high:
                return None
            result[key] = number
    return result
