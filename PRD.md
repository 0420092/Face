# PRD: AI 관상 분석 웹앱

## 1. 개요

| 항목 | 내용 |
|---|---|
| 제품명 | AI 관상가 (가칭) |
| 한 줄 설명 | 얼굴 사진을 업로드하면 OpenAI 이미지 분석 모델이 관상을 풀이해 주는 웹앱 |
| 기술 스택 | Python, Streamlit, OpenAI API (Vision 지원 모델), python-dotenv |
| 배포 | GitHub 저장소 → Streamlit Community Cloud |
| 성격 | 재미·엔터테인먼트용 서비스 (과학적 근거 없음을 명시) |

## 2. 목표

- 사용자가 사진 한 장만 올리면 몇 초 안에 전통 관상학 관점의 풀이를 받는다.
- 코드는 단순하게 유지해 GitHub에 올리고 Streamlit Cloud로 바로 배포할 수 있게 한다.
- API 키는 코드에 넣지 않는다. 로컬에서는 `.env`, 배포 환경에서는 Streamlit Secrets로 관리한다.

### 비목표 (이번 범위에서 제외)

- 회원가입/로그인, 결과 저장(DB)
- 여러 장 동시 분석, 궁합 보기
- 얼굴 인식으로 신원 확인, 나이·인종 등 민감 속성 추정

## 3. 대상 사용자

- 재미 삼아 자기 관상을 보고 싶은 일반 사용자
- 친구·가족 사진으로 결과를 공유하며 즐기려는 사용자

## 4. 사용자 흐름

1. 사용자가 웹앱에 접속한다.
2. 안내 문구와 면책 문구("재미로만 봐주세요")를 확인한다.
3. 얼굴 사진을 업로드한다 (JPG/PNG/WEBP). 모바일에서는 카메라 촬영(`st.camera_input`)도 가능하다.
4. 업로드한 사진이 미리보기로 표시된다.
5. "관상 보기" 버튼을 누른다.
6. 로딩 스피너("관상을 살펴보는 중...")가 표시된다.
7. 분석 결과가 항목별로 표시된다.
8. 다른 사진으로 다시 시도할 수 있다.

## 5. 기능 요구사항

### 5.1 이미지 업로드

| ID | 요구사항 | 우선순위 |
|---|---|---|
| F-01 | `st.file_uploader`로 jpg, jpeg, png, webp 업로드 지원 | 필수 |
| F-02 | 업로드 이미지 미리보기 표시 | 필수 |
| F-03 | 파일 크기 제한 (예: 10MB). 초과 시 에러 메시지 | 필수 |
| F-04 | 큰 이미지는 Pillow로 리사이즈(긴 변 1024px)해 API 비용과 지연을 줄임 | 권장 |
| F-05 | `st.camera_input`으로 카메라 촬영 지원 | 선택 |

### 5.2 관상 분석

| ID | 요구사항 | 우선순위 |
|---|---|---|
| F-10 | 이미지를 base64로 인코딩해 OpenAI Vision 모델에 전송 | 필수 |
| F-11 | 시스템 프롬프트로 "전통 관상학 전문가" 역할과 출력 형식을 지정 | 필수 |
| F-12 | 사진에 얼굴이 없거나 여러 명이면 그 사실을 알리고 다시 업로드를 안내 | 필수 |
| F-13 | 사용할 모델명은 환경변수 `OPENAI_MODEL`로 바꿀 수 있게 함 (기본값은 Vision 지원 모델, 예: `gpt-4o-mini`) | 필수 |
| F-14 | 분석 결과는 한국어로 출력 | 필수 |

### 5.3 결과 출력 항목

모델이 아래 구조의 마크다운으로 답하도록 프롬프트에 지정한다.

1. **첫인상 요약** – 한두 문장
2. **부위별 풀이** – 이마, 눈썹, 눈, 코, 입, 귀, 턱/얼굴형
3. **운세 풀이** – 재물운, 애정운, 직업운, 건강운
4. **성격과 강점**
5. **조언 한마디**
6. **종합 점수** – 100점 만점 (재미 요소)

추가 프롬프트 지침:
- 긍정적이고 존중하는 톤을 유지하고, 외모를 비하하거나 단정적인 부정 예언을 하지 않는다.
- 인종, 민족, 종교, 성적 지향, 건강 상태 같은 민감 속성은 추정하지 않는다.
- 실존 인물이 누구인지 식별하지 않는다.

### 5.4 UI

| ID | 요구사항 | 우선순위 |
|---|---|---|
| F-20 | 페이지 제목, 아이콘(🔮), 간단한 소개 문구 | 필수 |
| F-21 | 면책 문구 상시 표시 | 필수 |
| F-22 | 좌측: 사진, 우측: 결과의 2단 레이아웃 (모바일에서는 세로 배치) | 권장 |
| F-23 | 분석 중 `st.spinner` 표시 | 필수 |
| F-24 | 사이드바에 사용 방법과 개인정보 안내 | 권장 |

## 6. 비기능 요구사항

| 항목 | 요구사항 |
|---|---|
| 보안 | API 키를 코드나 저장소에 넣지 않는다. `.env`는 `.gitignore`에 추가한다. |
| 개인정보 | 업로드 이미지는 서버에 저장하지 않고 메모리에서만 처리한다. OpenAI API로 전송된다는 사실을 화면에 안내한다. |
| 성능 | 분석 응답은 보통 15초 이내 |
| 에러 처리 | API 키 누락, 인증 실패, 요청 한도 초과, 네트워크 오류를 사용자에게 알기 쉬운 메시지로 보여준다. |
| 비용 | 이미지 리사이즈와 `max_tokens` 제한으로 호출당 비용을 관리한다. |

## 7. 기술 설계

### 7.1 프로젝트 구조

```
관상/
├── app.py              # Streamlit 메인 앱
├── requirements.txt    # 의존성
├── .streamlit/
│   └── config.toml     # 업로드 제한, 오류 표시 방식, 테마
├── .env                # 로컬 전용 API 키 (Git에 올리지 않음)
├── .env.example        # 환경변수 예시 (Git에 올림)
├── .gitignore
├── README.md
└── PRD.md
```

> 참고: GitHub 저장소 이름과 폴더 이름은 영문(예: `face-reading-app`)을 권장한다. 한글 경로는 일부 도구에서 문제를 일으킬 수 있다.

### 7.2 의존성 (`requirements.txt`)

```
streamlit>=1.58
openai>=3.6
python-dotenv>=1.0
Pillow>=10.0
```

### 7.3 환경변수

`.env.example`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
MAX_ANALYSES_PER_SESSION=10
```

`MAX_ANALYSES_PER_SESSION`은 브라우저 탭(접속)당 API 호출 횟수 제한이다. 새로고침하면 초기화되므로 비용 보호의 주된 수단은 OpenAI 대시보드의 사용 한도 설정이다.

### 7.4 API 키 로딩 방식

Streamlit Cloud는 `.env` 파일을 읽지 않으므로(저장소에 올리지 않기 때문에) 두 환경을 모두 지원한다.

1. `load_dotenv()`로 로컬 `.env`를 읽는다.
2. `st.secrets`에 `OPENAI_API_KEY`가 있으면 그 값을 쓰고, 없으면 `os.getenv("OPENAI_API_KEY")`를 쓴다.
3. 둘 다 없으면 화면에 설정 방법을 안내하고 `st.stop()` 한다.

```python
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_secret(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass  # secrets.toml이 없는 로컬 환경
    return os.getenv(key, default)

api_key = get_secret("OPENAI_API_KEY")
model = get_secret("OPENAI_MODEL", "gpt-4o-mini")
```

### 7.5 OpenAI 호출 방식

- `openai` 공식 SDK의 Chat Completions API에 이미지를 `image_url`(data URL, base64) 형식으로 전달한다.
- `max_completion_tokens`는 1,500으로 제한한다. (openai 3.x SDK와 최신 모델은 `max_tokens` 대신 이 이름을 쓴다. 추론형 모델은 이 한도를 추론에 소진할 수 있으므로 일반 Vision 모델을 권장한다.)

```python
from openai import OpenAI
client = OpenAI(api_key=api_key)

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": "이 사진의 관상을 봐주세요."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]},
    ],
    max_completion_tokens=1500,
)
result = response.choices[0].message.content
```

### 7.6 `.gitignore` 필수 항목

```
.env
.streamlit/secrets.toml
__pycache__/
*.pyc
.venv/
venv/
```

## 8. 배포 절차

1. **로컬 실행 확인**
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
2. **GitHub 업로드**
   - 업로드 전에 `.env`가 `.gitignore`에 들어 있는지 확인한다.
   - `git init` → `git add .` → `git commit` → GitHub 원격 저장소에 push
3. **Streamlit Cloud 배포**
   - https://share.streamlit.io 에서 GitHub 계정 연결
   - 저장소, 브랜치(`main`), 메인 파일(`app.py`) 선택
   - **Advanced settings → Secrets**에 아래 내용 입력:
     ```toml
     OPENAI_API_KEY = "sk-..."
     OPENAI_MODEL = "gpt-4o-mini"
     ```
   - Deploy 클릭
4. 배포 URL로 접속해 업로드와 분석이 동작하는지 확인한다.

## 9. 면책 문구 (화면 표시용)

> 본 서비스는 재미를 위한 엔터테인먼트 콘텐츠이며, 관상 결과는 과학적 근거가 없습니다. 업로드한 사진은 저장되지 않으며, 분석을 위해 OpenAI API로 전송됩니다. 타인의 사진은 본인 동의를 받은 경우에만 사용해 주세요.

## 10. 완료 기준

- [ ] 로컬에서 `.env`의 키로 사진 업로드부터 결과 출력까지 동작한다.
- [ ] 얼굴이 없는 사진을 올리면 안내 메시지가 나온다.
- [ ] API 키가 없을 때 앱이 죽지 않고 설정 방법을 안내한다.
- [ ] GitHub 저장소에 `.env`가 포함되지 않는다.
- [ ] Streamlit Cloud에서 Secrets 설정만으로 정상 동작한다.
- [ ] 면책 문구와 개인정보 안내가 화면에 표시된다.

## 11. 향후 개선 아이디어

- 결과를 이미지 카드로 만들어 SNS 공유
- 두 사람 사진으로 궁합 보기
- 닮은 동물상 분석
- 결과 스트리밍 출력(`stream=True`)으로 체감 속도 개선
- 다국어(영어/일본어) 지원
