import re

from sqlalchemy import func

_TSQUERY_RESERVED = re.compile(r"[&|!():*'\\]")


def apply_text_search(
    query,
    model,
    text: str,
    *,
    tsv_attr: str = 'tsv',
    config: str = 'portuguese',
):
    if not text or not text.strip():
        return query

    parts = [p for p in (_TSQUERY_RESERVED.sub(' ', text).split()) if p]
    if not parts:
        return query

    prefix_query = ' & '.join(f'{p}:*' for p in parts[:12])
    ts_query = func.to_tsquery(config, prefix_query)

    tsv_col = getattr(model, tsv_attr)
    query = query.where(tsv_col.op('@@')(ts_query))
    query = query.order_by(func.ts_rank(tsv_col, ts_query).desc())
    return query
