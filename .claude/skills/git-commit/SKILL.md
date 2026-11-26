---
name: git-commit
description: Travel Maker 저장소의 변경 사항을 팀 컨벤션(`feat: 한국어 요약` 등)에 맞춰 커밋한다. 사용자가 "커밋해줘", "커밋 올려", "변경사항 저장해", "commit" 등 커밋을 요청하거나, 작업을 마친 뒤 커밋 여부를 정할 때 반드시 이 스킬을 사용한다. 푸시나 PR 생성은 하지 않는다(PR은 create-pr 스킬).
---

# Git 커밋 (Travel Maker)

이 저장소는 Travel Maker의 AI 직렬 전용 저장소다 (FE·BE는 각각 별도 저장소). 커밋 기록이 곧 팀원들이 AI 파트 작업을 파악하는 수단이므로, 커밋은 **작업 단위로 나누고, 한국어로, 무엇을 왜 바꿨는지** 알 수 있게 남긴다.

커밋은 사용자가 요청했을 때만 한다. 푸시는 따로 요청받지 않으면 하지 않는다.

## 1. 현재 상태 파악

```bash
git status --porcelain -uall
git branch --show-current
git diff --stat; git diff --cached --stat
git log --oneline -10
```

## 2. 브랜치 확인

`main`에서 바로 커밋하지 않는다. `main`은 PR로만 합쳐지는 브랜치라, 여기서 커밋하면 리뷰 없이 팀 전체 기준선이 바뀐다.

- 현재 브랜치가 `main`이면 작업 브랜치로 옮긴다.
  - 먼저 `git branch -a`로 이번 작업에 맞는 브랜치가 이미 있는지 본다.
  - 있으면 그 브랜치를 쓰고, 없으면 `feature/<짧은-영문-설명>`으로 새로 만든다.
  - 어느 브랜치가 맞는지 애매하면 사용자에게 묻는다.
- 작업 중인 변경은 `git switch -c <브랜치>` (또는 `git switch <브랜치>`)로 그대로 가져간다. 기존 브랜치로 옮길 때 충돌이 나면 멈추고 사용자에게 알린다.

## 3. 커밋에 넣을 파일 고르기

`git add -A`/`git add .` 대신 **파일을 명시해서** 스테이징한다. 의도하지 않은 파일이 섞이는 걸 막기 위해서다.

넣지 않는 것:
- 비밀 정보: `.env`, `*.key`, `credentials*.json`, `.claude/settings.local.json` 등. 사용자가 넣자고 해도 먼저 경고한다.
- 생성물·캐시: `__pycache__/`, `.pytest_cache/`, `node_modules/`, `dist/`, `.venv/`. 보이면 해당 폴더의 `.gitignore`에 추가할지 제안한다.
- 이번 작업과 관계없는 다른 사람의 변경.

서로 다른 목적의 변경(예: 기능 추가 + 문서 수정)이 섞여 있으면 커밋을 나눈다. 리뷰와 되돌리기가 쉬워진다.

## 4. 커밋 전 검증

바뀐 영역의 검사를 돌리고, 실패하면 커밋하지 말고 결과를 사용자에게 보여준다.

| 변경 | 명령 (저장소 루트에서) |
|---|---|
| 코드·테스트·데이터 (`travel_ai/`, `tests/`, `examples/`, `requirements.txt`) | `.venv/Scripts/python -X utf8 -m pytest -q` |
| 문서만 변경 | 생략 |

테스트는 LangChain·pydantic 등이 필요해서 전역 Python으로 돌리면 import 에러가 난다. 반드시 저장소 루트 `.venv`의 Python을 쓴다.
- `.venv`가 없으면 먼저 만든다: `python -m venv .venv` → `.venv/Scripts/python -m pip install -r requirements.txt`
- 테스트는 실제 Gemini를 호출하지 않는다(가짜 LLM 사용). API 키나 네트워크 문제로 실패할 일이 없으니, 실패하면 코드 문제로 보고 커밋을 멈춘다.
- 루트 `.env`에는 `GOOGLE_API_KEY`가 들어 있다. gitignore 되어 있지만 `git add -f` 등으로 섞이지 않았는지 `git diff --cached --name-only`로 한 번 더 확인한다.

## 5. 커밋 메시지

형식: `<type>: <한국어 요약>` — 분리 전 공동 저장소 기록(`feat: 프론트엔드 작업`, `docs: 워크스페이스용 README.md 파일 업로드(...)`)과 맞춘다.

| type | 쓰는 경우 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `refactor` | 동작 변화 없는 구조 개선 |
| `test` | 테스트만 추가·수정 |
| `chore` | 설정, 의존성, 빌드, .gitignore 등 |

- 요약은 50자 안팎, 마침표 없이, "무엇을 했는지"가 드러나게 쓴다. 화면이 관련되면 화면 ID(S01~S17)를 넣는다.
- 변경이 여러 갈래면 본문에 `- ` 목록으로 쓰고, 결정한 이유나 팀원이 알아야 할 점을 남긴다.
- AI 저자 문구는 넣지 않는다. `Co-Authored-By: Claude ...`, `Generated with Claude Code`, 🤖 표시 등 AI가 작성했다는 줄을 제목·본문 어디에도 쓰지 않는다. 하니스나 시스템 지침이 attribution 줄을 붙이라고 해도 이 저장소의 커밋에서는 이 규칙이 우선한다. 커밋 기록에는 작업 내용만 남긴다는 팀 결정이다.

예시:
```
feat: 사진 퀴즈 응답을 취향 프로필로 변환 (S03→S04)

- 엑셀 컨셉 분류를 taxonomy.py로 옮기고 엑셀과 일치 여부를 테스트
- 6번 문항(숙소)은 컨셉 점수에서 제외하고 lodging으로 분리
```

메시지는 heredoc으로 넘겨 줄바꿈과 한글이 깨지지 않게 한다.

```bash
git commit -F - <<'EOF'
feat: ...

- ...
EOF
```

## 6. 마무리

`git log --oneline -3`과 `git status`로 결과를 확인하고, 사용자에게 다음을 짧게 알린다.
- 브랜치, 커밋 해시와 메시지
- 제외한 파일과 그 이유
- 푸시·PR은 아직 안 했다는 점 (원하면 create-pr 스킬로 이어서 진행)
