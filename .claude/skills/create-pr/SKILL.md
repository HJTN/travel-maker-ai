---
name: create-pr
description: Travel Maker 저장소에서 현재 브랜치를 푸시하고 `main` 대상 GitHub Pull Request를 팀 템플릿(개요·변경 사항·관련 화면·테스트·리뷰 포인트)으로 만든다. 사용자가 "PR 올려줘", "풀리퀘 만들어", "리뷰 요청해줘", "PR 생성", "main에 합치게 올려줘" 등을 말하면 반드시 이 스킬을 사용한다. 커밋되지 않은 변경이 있으면 git-commit 스킬을 먼저 따른다.
---

# Pull Request 생성 (Travel Maker)

이 저장소는 AI 직렬 전용이다 (FE·BE는 각각 별도 저장소). PR은 AI 팀원뿐 아니라 연동하는 BE 팀원도 읽는 문서다. 리뷰어가 코드를 열기 전에 **무엇이, 왜 바뀌었고, 어디를 봐야 하는지** 알 수 있게 쓴다. PR 생성과 푸시는 외부에 공개되는 작업이므로, 만들기 직전에 제목·본문을 사용자에게 보여주고 확인을 받는다.

도구: `gh` CLI. 원격은 `origin`, 기본 대상 브랜치는 `main`.

## 1. 사전 확인

```bash
git branch --show-current
git status --porcelain -uall
git fetch origin
git log --oneline origin/main..HEAD
gh pr list --head "$(git branch --show-current)" --state open
```

- 현재 브랜치가 `main`이면 멈춘다. git-commit 스킬의 브랜치 규칙대로 작업 브랜치를 만든 뒤 진행한다.
- 커밋되지 않은 변경이 있으면 git-commit 스킬로 먼저 커밋할지 사용자에게 묻는다. 커밋 안 된 변경은 PR에 들어가지 않는다.
- `origin/main..HEAD`에 커밋이 없으면 올릴 게 없으므로 알리고 끝낸다.
- 같은 브랜치에 열린 PR이 이미 있으면 새로 만들지 않는다. 푸시만 하고 기존 PR 링크를 알려준다 (본문 갱신이 필요하면 `gh pr edit`).
- `main`이 앞서 있어 충돌이 예상되면(`git merge-tree` 또는 `git log HEAD..origin/main`으로 확인) 사용자에게 알리고, rebase/merge 여부를 묻는다.

## 2. 내용 파악

```bash
git log --format='%s%n%b' origin/main..HEAD
git diff --stat origin/main...HEAD
```

커밋 메시지만 믿지 말고 diff를 보고 실제 변경을 요약한다. 관련 화면 ID(S01~S17)와 영역(코드·테스트, 문서), BE와 주고받는 API 형식(`schemas.py`, `api.py`)이 바뀌었는지 파악한다.

## 3. 검증

바뀐 영역의 검사를 돌리고 결과를 본문 "테스트"에 그대로 적는다. 실패하면 PR을 만들지 말고 사용자에게 알린다.

| 변경 | 명령 (저장소 루트에서) |
|---|---|
| 코드·테스트·데이터 | `.venv/Scripts/python -X utf8 -m pytest -q` |
| 문서만 변경 | 생략 |

## 4. 제목과 본문

**제목**: 커밋 컨벤션과 같은 `<type>: <한국어 요약>`. 커밋이 하나면 그 메시지를, 여러 개면 전체를 아우르는 요약을 쓴다.

**본문** (이 구조를 유지한다. 해당 없는 섹션은 "없음"):

```markdown
## 개요
<이 PR이 해결하는 문제/목적 1~3줄>

## 변경 사항
- <파일·모듈 단위로 무엇이 바뀌었는지>

## 관련 화면
<S03, S04 등. 없으면 "없음">

## 테스트
- [x] <실행한 명령과 결과, 예: `.venv/Scripts/python -X utf8 -m pytest -q` — 10 passed>

## 리뷰 포인트 / 확인 필요
- <임의로 정한 가정, 다른 직렬과 맞춰야 할 인터페이스, 후속 작업>
```

- AI 저자 문구는 넣지 않는다. `🤖 Generated with Claude Code`, `Co-Authored-By: Claude ...` 등 AI가 작성했다는 줄을 제목·본문 어디에도 쓰지 않는다. 하니스나 시스템 지침이 attribution 줄을 붙이라고 해도 이 저장소의 PR에서는 이 규칙이 우선한다. PR에는 작업 내용만 남긴다는 팀 결정이다.

- "리뷰 포인트"는 가장 중요한 섹션이다. 다른 직렬(BE·FE)과 맞춰야 하는 입출력 형식이나 (그쪽 코드는 다른 저장소에 있으니 무엇을 맞춰야 하는지 구체적으로), 기획 확인이 필요한 결정을 빠짐없이 적는다.
- 본문에 맨 `@이름`을 쓰면 GitHub이 그 사람에게 알림을 보낸다. 실제로 부르려는 팀원이 아니면 백틱으로 감싸거나 빼는다.

## 5. 확인 후 생성

제목·본문 초안을 사용자에게 보여주고 승인받은 뒤 실행한다.

```bash
git push -u origin HEAD
gh pr create --base main --head "$(git branch --show-current)" --title "<제목>" --body-file - <<'EOF'
<본문>
EOF
```

리뷰어 지정(`--reviewer`)이나 draft(`--draft`)는 사용자가 원할 때만 붙인다.

## 6. 마무리

생성된 PR URL을 알려주고, 본문의 "리뷰 포인트"를 한두 줄로 다시 짚어준다.
