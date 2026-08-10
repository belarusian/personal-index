"""Test that content_enricher.py has no duplicate set elements (TICKET-57)."""
import ast


def test_negative_words_no_duplicates_in_source():
    """NEGATIVE_WORDS set should have no duplicate elements in source code."""
    source = open("personal_index/content_enricher.py").read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ContentEnricher":
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "NEGATIVE_WORDS":
                            if isinstance(item.value, ast.Set):
                                elts = [
                                    e.value for e in item.value.elts
                                    if isinstance(e, ast.Constant)
                                ]
                                assert len(elts) == len(set(elts)), (
                                    f"Duplicate elements in NEGATIVE_WORDS: "
                                    f"{[e for e in elts if elts.count(e) > 1]}"
                                )


def test_negative_words_no_wrong_duplicate():
    """Verify 'wrong' appears only once in NEGATIVE_WORDS source."""
    source = open("personal_index/content_enricher.py").read()
    # Count occurrences of "wrong" in the NEGATIVE_WORDS set definition
    lines = source.split("\n")
    in_negative = False
    wrong_count = 0
    for line in lines:
        if "NEGATIVE_WORDS" in line:
            in_negative = True
        if in_negative:
            wrong_count += line.count('"wrong"')
        if in_negative and line.strip().endswith("}"):
            break
    assert wrong_count == 1, f"'wrong' appears {wrong_count} times in NEGATIVE_WORDS"
