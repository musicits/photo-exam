"""문제은행 데이터가 깨지지 않았는지 확인한다.

문제를 추가하거나 고친 뒤에는 `python3 exam/build.py` 를 다시 돌리고
이 테스트를 실행하면 된다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EXAM = Path(__file__).resolve().parents[1]
DATA = EXAM / "data" / "questions.json"


@pytest.fixture(scope="module")
def bank():
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def questions(bank):
    return [q for sub in bank["subjects"] for q in sub["questions"]]


def test_과목이_셋이고_문항수가_맞는다(bank, questions):
    assert [s["no"] for s in bank["subjects"]] == [1, 2, 3]
    assert bank["total"] == len(questions)
    for sub in bank["subjects"]:
        assert len(sub["questions"]) >= 60, f'{sub["no"]}과목 문항이 부족하다'


def test_모든_문항의_형식이_올바르다(questions):
    for q in questions:
        assert q["q"].strip(), q["id"]
        assert len(q["c"]) == 4, q["id"]
        assert all(c.strip() for c in q["c"]), q["id"]
        assert 1 <= q["a"] <= 4, q["id"]
        assert len(q["e"].strip()) >= 20, f'{q["id"]}: 해설이 너무 짧다'
        assert q["topic"].strip(), q["id"]
        assert q["s"] in (1, 2, 3), q["id"]


def test_문항번호와_문제가_중복되지_않는다(questions):
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))
    texts = [q["q"] for q in questions]
    assert len(texts) == len(set(texts))


def test_한_문항_안에_같은_보기가_없다(questions):
    for q in questions:
        assert len(set(q["c"])) == 4, f'{q["id"]}: 보기가 중복된다'


def test_정답_번호가_한쪽에_몰리지_않는다(bank):
    """정답이 특정 번호에 몰리면 내용을 몰라도 찍어서 맞힐 수 있다."""
    for sub in bank["subjects"]:
        n = len(sub["questions"])
        for pos in (1, 2, 3, 4):
            share = sum(q["a"] == pos for q in sub["questions"]) / n
            assert 0.15 <= share <= 0.35, f'{sub["no"]}과목 정답 {pos}번 비율 {share:.0%}'


def test_모든_단원이_고르게_채워져_있다(bank, questions):
    """시중 교재 목차의 8개 단원을 빠짐없이 다룬다."""
    assert [c["no"] for c in bank["chapters"]] == [1, 2, 3, 4, 5, 6, 7, 8]
    counts = {c["no"]: 0 for c in bank["chapters"]}
    for q in questions:
        assert q["ch"] in counts, q["id"]
        counts[q["ch"]] += 1
    for no, n in counts.items():
        assert n >= 15, f"{no}장 문항이 {n}개뿐이다"


def test_웹페이지에_문제가_박혀_있다(bank):
    """build.py 가 quiz-template.html 에 데이터를 넣어 한 파일로 만든다."""
    page = (EXAM / "index.html").read_text(encoding="utf-8")
    assert "__EXAM_DATA__" not in page, "build.py 를 다시 실행해야 한다"
    assert "window.EXAM_DATA = {" in page
    assert bank["subjects"][0]["questions"][0]["q"] in page
