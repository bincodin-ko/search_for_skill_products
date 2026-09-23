---
name: reel-analyzer
description: 인스타그램 릴스 링크를 받아 캡션·화면 글자·음성 대본을 자동으로 모으고 내용을 분석한다. "릴스 분석해", "이 릴스 정리해줘", instagram.com/reel/ 또는 instagram.com/p/ 링크가 나오면 사용. 사용자 PC에서 크롬 연동(claude --chrome)으로 실행할 때 동작한다.
---

# reel-analyzer

사용자가 준 인스타 릴스를 **사용자 손을 빌리지 않고** 분석한다. 사용자는 링크만 준다. 설치·다운로드·받아쓰기는 전부 Claude가 한다.

## 원칙

- 릴스 내용을 추측으로 채우지 않는다. 못 얻은 정보는 "확보 실패"라고 적는다.
- 사용자에게 복사·붙여넣기를 요구하지 않는다. 막히면 다음 대체 경로로 넘어간다.
- 사용자에게 부탁해도 되는 것은 두 가지뿐: 크롬 탭에서 인스타 로그인, 권한 확인 창 승인.
- 다운로드한 영상·음성·캡처는 분석용으로만 쓰고 git에 커밋하지 않는다(`.gitignore` 처리됨).

## 변수

- `ID`: 링크의 `/reel/<ID>/` 또는 `/p/<ID>/` 부분
- `OUT`: `reels/<ID>` (저장소 루트 기준)
- `PY`: 가상환경 파이썬. Windows는 `.venv/Scripts/python.exe`, macOS·Linux는 `.venv/bin/python`
- `TOOLS`: `.claude/skills/reel-analyzer/scripts/reel_tools.py`

## 0단계: 준비 확인 (첫 실행 때만 오래 걸림)

1. 크롬 도구(이름에 `chrome`이 들어간 브라우저 도구)가 있는지 확인한다. 없으면 사용자에게 한 줄로 알리고 멈춘다: "`/exit` 후 `claude --chrome`으로 다시 실행해 주세요."
2. `PY`가 없으면 가상환경을 만든다.
   - Windows: `py -3 --version`으로 파이썬 확인 → 없으면 `winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements`
     - 설치 직후 `py`가 안 잡히면 `"$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"`를 직접 쓴다.
     - `python`은 Microsoft Store 바로가기일 수 있으니 `py -3`을 우선 쓴다.
   - `py -3 -m venv .venv` (macOS·Linux는 `python3 -m venv .venv`)
3. `PY -m pip install -r .claude/skills/reel-analyzer/requirements.txt`
4. `mkdir OUT`

## 1단계: 캡션·작성자 읽기

1. 크롬 도구로 릴스 링크를 새 탭에서 연다.
2. 로그인 화면이 나오면 사용자에게 "크롬 탭에서 인스타그램 로그인해 주세요"라고 알리고 기다린다.
3. 캡션이 "더 보기"로 접혀 있으면 눌러서 펼친 뒤 페이지 텍스트를 읽는다.
4. 페이지에서 JavaScript를 실행할 수 있으면 아래 값도 함께 가져온다.
   ```js
   ({
     og: document.querySelector('meta[property="og:description"]')?.content,
     title: document.title,
     datetime: document.querySelector('time')?.getAttribute('datetime'),
   })
   ```
5. `OUT/caption.md`에 저장: 링크, 작성자 @계정, 게시일, 캡션 원문(수정 없이 그대로).

## 2단계: 영상·음성 주소 모으기

1. 영상이 재생되도록 한 번 클릭하고 3초 기다린다.
2. 페이지에서 아래 JavaScript를 실행해 미디어 주소를 모은다.
   ```js
   (() => {
     const out = new Set();
     const html = document.documentElement.innerHTML;
     for (const m of html.matchAll(/"video_versions":\s*\[(.*?)\]/g)) {
       for (const u of m[1].matchAll(/"url":"(.*?)"/g)) out.add(JSON.parse('"' + u[1] + '"'));
     }
     for (const e of performance.getEntriesByType('resource')) {
       if (/\.mp4(\?|$)/.test(e.name)) out.add(e.name);
     }
     const v = document.querySelector('video')?.src;
     if (v && v.startsWith('http')) out.add(v);
     return [...out].join('\n');
   })()
   ```
3. 결과가 비었으면 네트워크 요청 읽기 도구로 `mp4`가 들어간 요청을 찾는다. 그래도 없으면 페이지를 새로고침하고 1~2를 한 번 더 한다.
4. 모은 주소를 `OUT/media_urls.txt`에 한 줄씩 저장한다.
5. `PY TOOLS urls OUT/media_urls.txt` → 각 줄이 `종류<TAB>주소`로 나온다.
   - `progressive`: 영상+음성이 한 파일 (가장 좋음)
   - `audio` / `video`: 따로 나뉜 트랙
   - `unknown`: 판별 불가 → 받아서 `probe`로 확인

## 3단계: 다운로드

- `progressive`가 있으면: `PY TOOLS download "<주소>" OUT/media.mp4`
- 없으면: `audio` → `OUT/audio.mp4`, `video` → `OUT/video.mp4`
- `unknown`만 있으면 하나씩 받아서 `PY TOOLS probe <파일>`로 음성·영상 스트림을 확인한다.
- HTTP 403·410이면 주소가 만료된 것 → 페이지를 새로고침하고 2단계부터 한 번만 다시 한다.

## 4단계: 받아쓰기

```
PY TOOLS transcribe OUT/media.mp4 OUT
```
- 음성 트랙이 따로면 `OUT/audio.mp4`를 넣는다.
- 첫 실행은 모델(약 1.6GB) 다운로드로 오래 걸린다. 사용자에게 "음성 모델 받는 중, 약 5분"이라고 한 줄 알린다.
- 메모리 부족 등으로 실패하면 `--model small`로 다시 한다.
- 결과: `OUT/transcript.txt` (`[분:초] 문장` 형식)
- 한국어가 아닌 릴스면 `--lang auto`

## 5단계: 화면 글자 읽기

```
PY TOOLS frames OUT/media.mp4 OUT/frames --max 15
```
- 영상 트랙이 따로면 `OUT/video.mp4`를 넣는다.
- 저장된 PNG를 하나씩 읽고(Read 도구) 화면에 나온 글자를 `OUT/onscreen.md`에 `[초] 글자` 형식으로 적는다. 같은 글자가 반복되면 한 번만 적는다.
- 영상을 못 받았으면: 크롬에서 영상을 재생하며 3~5초 간격으로 스크린샷을 찍어 같은 작업을 한다.

## 6단계: 분석 작성

`OUT/analysis.md`를 아래 틀로 쓴다. 근거는 캡션·대본·화면 글자에서만 가져오고, 인용에는 `[분:초]`를 붙인다.

```markdown
# 릴스 분석: <한줄 제목>
- 링크 / 작성자 / 게시일 / 길이
- 확보 상태: 캡션 O/X · 음성 대본 O/X · 화면 글자 O/X

## 한줄 요약
## 핵심 주장 (원문 인용 + 타임스탬프)
## 단계별 방법 (릴스가 알려주는 순서 그대로)
## 따라 할 수 있나
- 필요한 도구·비용·시간
- 전제 조건(팔로워, 자본, 기술 등)
## 냉정한 평가
- 근거가 있는 주장 / 근거 없는 주장
- 과장된 부분, 빠진 부분(비용, 실패 사례, 법적 문제)
- (돈 버는 방법 릴스라면) 원문 근거 · 돈을 낸 흔적 · 고객에게 닿을 경로가 있는가
## Claude로 옮기는 법
- 바로 쓸 프롬프트 1~3개, 또는 스킬로 만들 단계
## 바로 할 일 1개
```

## 7단계: 보고

채팅에는 짧게만 쓴다.
1. 첫 줄: 한줄 요약
2. 핵심 3개
3. 냉정한 평가 한 줄
4. 파일 위치: `OUT/analysis.md`
5. 확보 실패한 항목이 있으면 무엇이 왜 실패했는지 한 줄

## 8단계: 결과 올리기 (클라우드 세션과 공유)

텍스트 결과만 커밋해서 GitHub에 올린다. 영상·음성·캡처는 `.gitignore`로 빠진다.
```
git add reels/<ID>/*.md reels/<ID>/transcript.*
git commit -m "Add reel analysis <ID>"
git push
```
- 푸시하면 클라우드의 Claude 세션도 `git pull`로 같은 결과를 읽을 수 있다.
- 푸시가 GitHub 로그인을 요구하면 사용자에게 뜨는 로그인 창에서 한 번만 로그인해 달라고 알린다.

## 문제 해결

| 증상 | 원인 | 대응 |
|---|---|---|
| 미디어 주소 0개 | 영상이 아직 안 불러와짐 | 영상 클릭 → 5초 대기 → 다시 실행, 그래도 없으면 새로고침 |
| 다운로드 403/410 | 주소 만료(몇 시간 유효) | 새로고침 후 2단계부터 다시 |
| `model load failed` | 모델 다운로드 실패(네트워크) 또는 메모리 부족 | 네트워크면 잠시 후 재시도, 메모리면 `--model small` |
| 대본이 비어 있음 | 음악만 있는 릴스 | 화면 글자·캡션으로 분석하고 "음성 없음" 표시 |
| `py`를 못 찾음 | 파이썬 설치 직후 PATH 미반영 | `$env:LOCALAPPDATA\Programs\Python\Python312\python.exe` 직접 사용 |
