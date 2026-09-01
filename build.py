#!/usr/bin/env python3
"""exam/parts/*.json 을 합쳐 문제은행 데이터·웹페이지·마크다운을 만든다.

- 보기를 회전시켜 정답이 특정 번호에 몰리지 않게 맞춘다
- 문항마다 시험 과목(1~3)과 교재 단원(1~8)을 함께 붙인다
- quiz-template.html 에 문제 데이터를 그대로 박아 index.html 한 파일로 만든다
"""
import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent
PARTS = BASE / "parts"
DATA = BASE / "data"
PAGE = BASE / "index.html"

SUBJECTS = {
    1: ("사진일반", ["s1a", "s1b", "s1c", "s1d", "s1e"]),
    2: ("사진재료 및 현상", ["s2a", "s2b", "s2c", "s2d", "s2e"]),
    3: ("사진기계 및 촬영", ["s3a", "s3b", "s3c", "s3d", "s3e"]),
}

# 시중 교재의 단원 구성. 시험 과목과는 나누는 기준이 달라 따로 붙인다.
CHAPTERS = {
    1: "사진의 역사",
    2: "광학의 기초",
    3: "색채의 기초",
    4: "사진장비 및 관리",
    5: "사진 조명",
    6: "디지털 이미지 프로세싱",
    7: "아날로그 사진",
    8: "사진 제작 계획과 촬영",
}

TOPIC_CHAPTER = {
    "사진사": 1, "사진일반": 1,
    "빛의 성질": 2, "광학": 2, "렌즈수차": 2, "측광 단위": 2,
    "색채": 3, "시각": 3, "색온도": 3,
    "카메라구조": 4, "렌즈": 4, "조리개": 4, "심도": 4, "셔터": 4,
    "촬영모드": 4, "초점": 4,
    "노출계": 4, "필터": 4, "뷰카메라": 4, "카메라관리": 4, "안전·환경": 4,
    "조명": 5, "조명기구": 5, "광원": 5, "라이팅": 5, "플래시": 5,
    "디지털": 6, "디지털편집": 6, "색관리": 6,
    "필름구조": 7, "감광재료": 7, "잠상": 7, "감광도": 7, "필름특성": 7,
    "필름종류": 7, "필름보관": 7, "특성곡선": 7, "상반칙불궤": 7,
    "흑백현상": 7, "현상": 7, "현상액": 7, "정지액": 7, "정착액": 7,
    "수세": 7, "증감현상": 7, "인화": 7, "암실": 7, "컬러현상": 7, "보존": 7,
    "노출": 8, "구도": 8, "촬영": 8, "촬영기법": 8,
    "촬영계획": 8, "법·윤리": 8, "인물촬영": 8, "제품촬영": 8,
}


def rotate(choices, answer_idx, r):
    """보기를 오른쪽으로 r 칸 회전시키고 옮겨진 정답 위치를 돌려준다."""
    n = len(choices)
    r %= n
    new = choices[-r:] + choices[:-r] if r else list(choices)
    return new, (answer_idx + r) % n


def main():
    DATA.mkdir(exist_ok=True)
    subjects = []
    total = 0
    for num, (name, part_names) in SUBJECTS.items():
        questions = []
        for pn in part_names:
            questions += json.loads((PARTS / f"{pn}.json").read_text(encoding="utf-8"))

        # 정답 위치가 1~4 에 고르게 퍼지도록 목표 위치를 배분한다 (시드 고정)
        targets = [i % 4 for i in range(len(questions))]
        random.Random(1000 + num).shuffle(targets)

        for q, target in zip(questions, targets):
            assert len(q["c"]) == 4, q["id"]
            assert q["topic"] in TOPIC_CHAPTER, f'{q["id"]}: 분야 "{q["topic"]}" 의 단원이 정해지지 않았다'
            r = (target - (q["a"] - 1)) % 4
            new_choices, new_idx = rotate(q["c"], q["a"] - 1, r)
            q["c"] = new_choices
            q["a"] = new_idx + 1
            q["s"] = num
            q["ch"] = TOPIC_CHAPTER[q["topic"]]

        subjects.append({"no": num, "name": name, "questions": questions})
        total += len(questions)

    payload = {
        "title": "사진기능사 필기 예상문제은행",
        "total": total,
        "subjects": subjects,
        "chapters": [{"no": n, "name": CHAPTERS[n]} for n in sorted(CHAPTERS)],
    }

    (DATA / "questions.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    write_page(payload)
    write_markdown(payload)
    report(payload)


def write_page(payload):
    """문제 데이터를 박아 넣어 인터넷 없이도 열리는 한 파일짜리 페이지를 만든다."""
    template = (BASE / "quiz-template.html").read_text(encoding="utf-8")
    marker = "__EXAM_DATA__"
    assert marker in template, "quiz-template.html 에 데이터 자리표시자가 없다"
    PAGE.write_text(
        template.replace(marker, json.dumps(payload, ensure_ascii=False)), encoding="utf-8"
    )


def write_markdown(payload):
    circled = ["①", "②", "③", "④"]
    by_chapter = {n: [] for n in CHAPTERS}
    for sub in payload["subjects"]:
        for q in sub["questions"]:
            by_chapter[q["ch"]].append(q)

    index = ["# 사진기능사 필기 예상문제은행", "",
             f'총 {payload["total"]}문항. 정답과 해설은 문제마다 접혀 있습니다.', "",
             "## 시험 과목별", ""]
    for sub in payload["subjects"]:
        path = f'문제은행_{sub["no"]}과목_{sub["name"].replace(" ", "")}.md'
        index.append(f'- [{sub["no"]}과목 {sub["name"]}]({path}) · {len(sub["questions"])}문항')
        dump(BASE / path, f'{sub["no"]}과목 · {sub["name"]}', sub["questions"], circled)
    index += ["", "## 교재 단원별", ""]
    for n in sorted(CHAPTERS):
        path = f"단원_{n}_{CHAPTERS[n].replace(' ', '')}.md"
        index.append(f'- [{n}장 {CHAPTERS[n]}]({path}) · {len(by_chapter[n])}문항')
        dump(BASE / path, f"{n}장 · {CHAPTERS[n]}", by_chapter[n], circled)
    (BASE / "문제은행.md").write_text("\n".join(index) + "\n", encoding="utf-8")


def dump(path, heading, questions, circled):
    lines = [f"# {heading}", "", f"문항 수 {len(questions)}개.", ""]
    for i, q in enumerate(questions, 1):
        lines += [f'### {i}. {q["q"]}', ""]
        lines += [f"- {circled[j]} {c}" for j, c in enumerate(q["c"])]
        lines += ["", "<details><summary>정답 보기</summary>", "",
                  f'**정답 {circled[q["a"]-1]}**  ·  {q["ch"]}장 {CHAPTERS[q["ch"]]}'
                  f'  ·  분야: {q["topic"]}  ·  문항번호: {q["id"]}', "",
                  q["e"], "", "</details>", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def report(payload):
    print(f'총 {payload["total"]}문항')
    seen_id, seen_q = set(), set()
    chapters = {}
    for sub in payload["subjects"]:
        dist = {1: 0, 2: 0, 3: 0, 4: 0}
        for q in sub["questions"]:
            assert q["id"] not in seen_id, f'중복 id: {q["id"]}'
            assert q["q"] not in seen_q, f'중복 문제: {q["id"]}'
            seen_id.add(q["id"])
            seen_q.add(q["q"])
            dist[q["a"]] += 1
            chapters[q["ch"]] = chapters.get(q["ch"], 0) + 1
        print(f'  {sub["no"]}과목 {sub["name"]}: {len(sub["questions"])}문항, 정답분포 {dist}')
    print("  단원별: " + ", ".join(
        f"{n}장 {CHAPTERS[n]} {chapters.get(n,0)}" for n in sorted(CHAPTERS)))


if __name__ == "__main__":
    main()
