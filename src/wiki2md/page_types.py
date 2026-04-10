PERSON_LABELS = {
    "en": {"born", "occupation", "spouse", "children"},
    "zh": {"出生", "职业", "職業", "配偶", "儿女", "子女"},
}


def infer_page_type(*, title: str, lang: str, infobox_labels: list[str]) -> str:
    normalized_labels = {label.casefold() for label in infobox_labels if label}
    person_labels = {label.casefold() for label in PERSON_LABELS.get(lang, set())}
    if normalized_labels & person_labels:
        return "person"

    lowered_title = title.casefold()
    if lowered_title.startswith("list of ") or lowered_title.startswith("timeline of "):
        return "list"

    return "article"
