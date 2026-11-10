# 🔮 AI 관상가

얼굴 사진을 업로드하면 OpenAI 이미지 분석 모델이 전통 관상학 관점에서 관상을 풀이해 주는 Streamlit 웹앱입니다.

> 재미를 위한 엔터테인먼트 콘텐츠이며, 결과는 과학적 근거가 없습니다.

## 로컬 실행

1. 패키지 설치

   ```
   pip install -r requirements.txt
   ```

2. `.env.example`을 복사해 `.env`를 만들고 API 키를 입력

   ```
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   MAX_ANALYSES_PER_SESSION=10
   ```

   - `OPENAI_MODEL`: 이미지 입력을 지원하는 일반 모델을 쓰세요. 추론형 모델은 응답이 비어 나올 수 있습니다.
   - `MAX_ANALYSES_PER_SESSION`: 브라우저 탭(접속)당 분석 횟수 제한입니다. 생략하면 10회입니다.

3. 실행

   ```
   streamlit run app.py
   ```

   브라우저에서 http://localhost:8501 이 열립니다.

## 설정 파일

`.streamlit/config.toml`에 다음 설정이 들어 있습니다.

- `server.maxUploadSize = 10`: 업로드 용량 제한(MB). `app.py`의 `MAX_FILE_MB`와 같은 값으로 유지하세요.
- `client.showErrorDetails = "none"`: 예상치 못한 오류가 나도 화면에 오류 내용·파일 경로를 보여주지 않습니다. 자세한 내용은 터미널 로그에서 확인하세요.
- `[theme.light]`, `[theme.dark]`: 화면 색상

## Streamlit Cloud 배포

1. 이 저장소를 GitHub에 push합니다. (`.env`는 `.gitignore`에 포함되어 올라가지 않습니다.)
2. https://share.streamlit.io 에서 GitHub 계정을 연결하고 저장소, 브랜치(`main`), 메인 파일(`app.py`)을 선택합니다.
3. **Advanced settings → Secrets**에 아래 내용을 입력합니다.

   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   MAX_ANALYSES_PER_SESSION = 10
   ```

4. **Deploy**를 누릅니다.

### 비용 관리 (배포 전 필수)

공개 URL은 누구나 접속할 수 있고, 모든 분석 비용은 내 API 키로 청구됩니다. 앱의 횟수 제한은 새로고침하면 초기화되므로, **OpenAI 대시보드(Settings → Limits)에서 월 사용 한도를 꼭 설정하세요.**

## 개인정보

업로드한 사진은 서버에 저장되지 않고 메모리에서만 처리되며, 분석을 위해 OpenAI API로 전송됩니다.
