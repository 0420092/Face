"""AI 관상가 - 얼굴 사진을 업로드하면 OpenAI 이미지 분석 모델이 관상을 풀이해 주는 Streamlit 앱."""

import base64
import hashlib
import io
import os
import re
import warnings

import openai
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageOps, UnidentifiedImageError

APP_TITLE = "AI 관상가"
APP_ICON = "🔮"
DEFAULT_MODEL = "gpt-4o-mini"
ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]
MAX_FILE_MB = 10  # .streamlit/config.toml의 server.maxUploadSize와 맞춘다
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000  # 4천만 화소(예: 8000x5000)를 넘는 이미지는 거부
MAX_IMAGE_SIDE = 1024
MAX_COMPLETION_TOKENS = 1500
DEFAULT_MAX_ANALYSES = 10  # 세션(브라우저 탭)당 API 호출 횟수 제한
PREVIEW_WIDTH = 320

NO_FACE = "NO_FACE"
MULTIPLE_FACES = "MULTIPLE_FACES"
SENTINEL_PATTERN = re.compile(rf"^\W*({NO_FACE}|{MULTIPLE_FACES})\b")

SOURCE_UPLOAD = "📁 사진 업로드"
SOURCE_CAMERA = "📷 카메라 촬영"

DISCLAIMER = (
    "본 서비스는 재미를 위한 엔터테인먼트 콘텐츠이며, 관상 결과는 과학적 근거가 없습니다. "
    "업로드한 사진은 저장되지 않으며, 분석을 위해 OpenAI API로 전송됩니다. "
    "타인의 사진은 본인 동의를 받은 경우에만 사용해 주세요."
)

SYSTEM_PROMPT = f"""당신은 수십 년 경력의 전통 관상학 전문가입니다. 사용자가 보낸 얼굴 이미지를 보고 관상을 풀이합니다.

## 먼저 확인할 것
- 실제 사진뿐 아니라 그림, 초상화, 일러스트, 캐릭터라도 사람의 얼굴(눈·코·입)이 알아볼 수 있게 보이면 풀이 대상입니다.
- 이미지에 사람 얼굴이 전혀 없거나, 너무 흐리거나 가려져 눈·코·입을 알아볼 수 없을 때만 다른 말 없이 `{NO_FACE}` 한 단어만 답하세요.
- 비슷한 크기의 얼굴이 두 개 이상 뚜렷하게 있어 누구를 풀이할지 정할 수 없을 때만 다른 말 없이 `{MULTIPLE_FACES}` 한 단어만 답하세요.
  주인공 얼굴이 하나 뚜렷하고 배경에 작은 사람이 있는 정도라면 주인공을 풀이하세요.
- 판단이 애매하면 신호 단어를 쓰지 말고 풀이를 하세요.

## 출력 형식
풀이할 때는 아래 마크다운 구조를 그대로 따라 한국어로 답하세요.

### 🌟 첫인상
한두 문장으로 전체 인상을 요약합니다.

### 👁️ 부위별 풀이
- **이마:**
- **눈썹:**
- **눈:**
- **코:**
- **입:**
- **귀:** (보이지 않으면 보이지 않는다고 쓰세요)
- **턱과 얼굴형:**

### 🍀 운세 풀이
- **재물운:**
- **애정운:**
- **직업운:**
- **건강운:**

### 💪 성격과 강점
2~3문장

### 💌 조언 한마디
한 문장

### 🏆 종합 점수
**NN점** / 100점 — 한 줄 평

## 지켜야 할 원칙
- 긍정적이고 따뜻하며 존중하는 말투를 쓰세요. 아쉬운 점도 보완 방법과 함께 부드럽게 표현하세요.
- 외모를 비하하거나 평가하지 말고, 불행·질병·죽음 같은 단정적인 부정 예언을 하지 마세요.
- 인종, 민족, 종교, 성적 지향, 건강 상태, 장애 여부를 추정하거나 언급하지 마세요.
- 이미지 속 인물이 누구인지(실존 인물, 유명인, 유명 작품 속 인물) 식별하거나 추측하지 마세요.
- 전통 관상학 용어(예: 천정, 인당, 준두, 지각)를 적절히 섞되 쉽게 풀어 설명하세요.
- 종합 점수는 재미 요소이므로 70~98점 사이에서 매기세요.
"""

load_dotenv()

# 픽셀 수가 지나치게 큰 이미지는 Pillow 단계에서 바로 오류가 나도록 한다
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

def get_secret(key: str, default: str | None = None) -> str | None:
    """st.secrets를 먼저 보고, 없으면 환경변수(.env)를 사용한다."""
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass  # 로컬에 secrets.toml이 없으면 st.secrets 접근 시 예외가 난다
    return os.getenv(key, default)


def get_model() -> str:
    return get_secret("OPENAI_MODEL") or DEFAULT_MODEL


def get_max_analyses() -> int:
    try:
        return max(1, int(get_secret("MAX_ANALYSES_PER_SESSION") or DEFAULT_MAX_ANALYSES))
    except ValueError:
        return DEFAULT_MAX_ANALYSES


def load_api_key() -> str:
    """API 키를 읽는다. 없으면 설정 방법과 면책 문구를 보여주고 앱을 멈춘다."""
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        st.error(
            "OpenAI API 키가 설정되지 않았습니다.\n\n"
            "- **로컬 실행:** 프로젝트 폴더의 `.env` 파일에 `OPENAI_API_KEY=sk-...`를 추가하세요.\n"
            "- **Streamlit Cloud:** 앱 설정의 **Secrets**에 `OPENAI_API_KEY = \"sk-...\"`를 추가하세요."
        )
        render_footer()
        st.stop()
    return api_key


# ---------------------------------------------------------------------------
# 이미지 처리
# ---------------------------------------------------------------------------

class ImageError(Exception):
    """사용자에게 그대로 보여줄 이미지 관련 오류."""


def prepare_image(raw: bytes) -> bytes:
    """원본 이미지를 검증하고, 회전 보정·RGB 변환·리사이즈 후 JPEG 바이트로 돌려준다."""
    if len(raw) > MAX_FILE_BYTES:
        size_mb = len(raw) / 1024 / 1024
        raise ImageError(f"파일이 너무 큽니다 ({size_mb:.1f}MB). {MAX_FILE_MB}MB 이하의 사진을 올려주세요.")

    try:
        with warnings.catch_warnings():
            # 한도를 넘는 큰 이미지는 경고 대신 오류로 처리한다
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(raw))
            img.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ImageError("이미지 해상도가 너무 큽니다. 일반적인 크기의 사진을 올려주세요.") from e
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ImageError("이미지 파일을 읽을 수 없습니다. 손상되지 않은 JPG, PNG, WEBP 파일을 올려주세요.") from e

    try:
        img = ImageOps.exif_transpose(img)

        if img.mode != "RGB":
            # 투명 배경은 흰색으로 채운다 (그냥 convert하면 검은색이 될 수 있음)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img = img.convert("RGBA")
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")

        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        raise ImageError("이미지를 처리하지 못했습니다. 다른 사진으로 다시 시도해 주세요.") from e


# ---------------------------------------------------------------------------
# 관상 분석
# ---------------------------------------------------------------------------

class EmptyResponseError(Exception):
    """모델이 내용 없는 응답을 돌려준 경우."""


def analyze_face(jpeg_bytes: bytes, api_key: str, model: str) -> str:
    """OpenAI Vision 모델에 이미지를 보내 관상 풀이(마크다운)를 받는다."""
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 이미지의 관상을 봐주세요."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )
    choice = response.choices[0]
    content = (choice.message.content or "").strip()
    if not content:
        if choice.finish_reason == "length":
            raise EmptyResponseError(
                f"`{model}` 모델이 답을 쓰기 전에 토큰 한도에 걸렸습니다. "
                "추론형 모델 대신 이미지 입력을 지원하는 일반 모델(예: gpt-4o-mini)을 사용해 주세요."
            )
        raise EmptyResponseError(choice.message.refusal or "모델이 빈 응답을 돌려주었습니다. 다시 시도해 주세요.")
    if choice.finish_reason == "length":
        content += "\n\n_(응답이 길어 일부가 잘렸을 수 있습니다.)_"
    return content


def classify_result(result: str) -> str | None:
    """결과가 얼굴 판정 신호 단어로 시작하면 그 신호를, 아니면 None을 돌려준다."""
    match = SENTINEL_PATTERN.match(result.strip())
    return match.group(1) if match else None


def describe_api_error(e: Exception, model: str) -> str:
    """OpenAI 예외를 사용자용 한국어 메시지로 바꾼다. (하위 클래스부터 검사)"""
    if isinstance(e, EmptyResponseError):
        return str(e)
    if isinstance(e, openai.AuthenticationError):
        return "API 키가 올바르지 않습니다. `.env` 또는 Streamlit Secrets의 `OPENAI_API_KEY`를 확인해 주세요."
    if isinstance(e, openai.PermissionDeniedError):
        return f"이 API 키로는 `{model}` 모델을 사용할 권한이 없습니다."
    if isinstance(e, openai.NotFoundError):
        return f"`{model}` 모델을 찾을 수 없습니다. `OPENAI_MODEL` 설정을 확인해 주세요."
    if isinstance(e, openai.RateLimitError):
        return "요청이 너무 많거나 API 사용 한도(크레딧)를 초과했습니다. 잠시 후 다시 시도하거나 OpenAI 결제 상태를 확인해 주세요."
    if isinstance(e, openai.BadRequestError):
        return f"요청이 거부되었습니다. `{model}` 모델이 이미지 입력을 지원하는지 확인해 주세요."
    if isinstance(e, openai.APITimeoutError):
        return "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(e, openai.APIConnectionError):
        return "OpenAI 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요."
    if isinstance(e, openai.APIError):
        return "OpenAI 서버에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    return "분석 중 알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
/* 제목 아래 부제 */
.app-subtitle { opacity: 0.75; margin-top: -0.75rem; margin-bottom: 1.5rem; }
/* 결과 섹션 제목 간격 */
[data-testid="stVerticalBlockBorderWrapper"] h3 { padding-top: 0; font-size: 1.3rem; }
/* 종합 점수 숫자 강조 */
[data-testid="stMetricValue"] { font-weight: 700; }
</style>
"""

SCORE_PATTERN = re.compile(r"\*\*\s*(\d{1,3})\s*점\s*\*\*")


def render_header() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown(
        '<p class="app-subtitle">얼굴 사진 한 장으로 보는 전통 관상 풀이</p>',
        unsafe_allow_html=True,
    )


def render_sidebar(model: str):
    """사이드바를 그리고, 남은 분석 횟수를 나중에 채울 자리를 돌려준다."""
    with st.sidebar:
        st.header("사용 방법")
        st.markdown(
            "1. 얼굴이 정면으로 잘 보이는 사진을 올리거나 촬영합니다.\n"
            "2. **관상 보기** 버튼을 누릅니다.\n"
            "3. 부위별 풀이와 운세, 종합 점수를 확인합니다."
        )
        st.divider()
        st.header("개인정보 안내")
        st.markdown(
            "- 사진은 서버에 **저장되지 않고** 메모리에서만 처리됩니다.\n"
            "- 분석을 위해 사진이 **OpenAI API로 전송**됩니다.\n"
            "- 다른 사람의 사진은 본인 동의를 받은 경우에만 사용해 주세요."
        )
        st.divider()
        st.caption(f"분석 모델: `{model}`")
        return st.empty()


def render_remaining(placeholder) -> None:
    used = st.session_state.get("analysis_count", 0)
    placeholder.caption(f"이번 접속에서 남은 분석 횟수: {max(0, get_max_analyses() - used)}회")


def render_footer() -> None:
    st.divider()
    st.caption(DISCLAIMER)


def reset() -> None:
    """업로드/촬영 위젯을 새로 만들고 입력 방식을 '사진 업로드'로 되돌린다."""
    st.session_state["input_version"] = st.session_state.get("input_version", 0) + 1
    st.session_state["source"] = SOURCE_UPLOAD
    st.session_state["source_last"] = SOURCE_UPLOAD


def keep_source_selected() -> None:
    """선택된 버튼을 다시 눌러 선택이 해제되면 이전 선택으로 되돌린다."""
    if st.session_state.get("source") is None:
        st.session_state["source"] = st.session_state.get("source_last", SOURCE_UPLOAD)
    st.session_state["source_last"] = st.session_state["source"]


def get_image_input():
    """업로드 또는 카메라 촬영으로 받은 이미지 파일을 반환한다. 없으면 None."""
    version = st.session_state.get("input_version", 0)
    st.session_state.setdefault("source", SOURCE_UPLOAD)
    source = st.segmented_control(
        "사진 입력 방식",
        [SOURCE_UPLOAD, SOURCE_CAMERA],
        label_visibility="collapsed",
        key="source",
        on_change=keep_source_selected,
    )
    if source == SOURCE_CAMERA:
        return st.camera_input("정면을 바라보고 촬영하세요", key=f"camera_{version}")
    image_file = st.file_uploader(
        f"얼굴 사진을 업로드하세요 (최대 {MAX_FILE_MB}MB)",
        type=ALLOWED_TYPES,
        key=f"upload_{version}",
    )
    st.caption(f"⚠️ 파일 옆에 빨간 표시가 뜨면 {MAX_FILE_MB}MB를 넘거나 지원하지 않는 형식입니다.")
    return image_file


def split_sections(result: str) -> list[str]:
    """'### ' 제목 기준으로 결과 마크다운을 섹션별로 나눈다."""
    parts = re.split(r"(?m)^(?=###\s)", result)
    return [p.strip() for p in parts if p.strip()]


def render_score(section: str) -> bool:
    """종합 점수 섹션을 강조 카드로 그린다. 점수를 못 찾으면 False."""
    match = SCORE_PATTERN.search(section)
    if not match:
        return False
    comment = section[match.end():].strip()
    comment = re.sub(r"^/\s*100\s*점\s*[—\-–:]*\s*", "", comment).strip()
    with st.container(border=True):
        left, right = st.columns([1, 2], vertical_alignment="center")
        left.metric("🏆 종합 점수", f"{match.group(1)}점")
        if comment:
            right.markdown(comment)
    return True


def render_result(result: str) -> None:
    signal = classify_result(result)
    if signal == NO_FACE:
        st.warning("사진에서 얼굴을 찾지 못했습니다. 얼굴이 정면으로 잘 보이는 사진을 올려주세요.")
        return
    if signal == MULTIPLE_FACES:
        st.warning("여러 사람의 얼굴이 보입니다. 한 사람만 나온 사진을 올려주세요.")
        return

    sections = split_sections(result)
    # 종합 점수를 맨 위에 먼저 보여준다
    score_sections = [s for s in sections if "종합 점수" in s.splitlines()[0]]
    if score_sections and render_score(score_sections[0]):
        sections = [s for s in sections if s is not score_sections[0]]

    for section in sections:
        with st.container(border=True):
            st.markdown(section)


def render_empty_state() -> None:
    with st.container(border=True):
        st.markdown(
            "#### 🔮 관상 풀이가 여기에 표시됩니다\n"
            "사진을 올리고 **관상 보기**를 눌러주세요.\n\n"
            "첫인상, 부위별 풀이, 재물·애정·직업·건강운, 종합 점수까지 알려드립니다."
        )


def run_analysis(jpeg_bytes: bytes, cache_key: str, api_key: str, model: str) -> None:
    """횟수 제한을 확인하고 분석을 실행해 결과를 캐시에 저장한다. 오류는 이 자리에 표시한다."""
    max_analyses = get_max_analyses()
    used = st.session_state.get("analysis_count", 0)
    if used >= max_analyses:
        st.warning(f"이번 접속에서 사용할 수 있는 분석 {max_analyses}회를 모두 사용했습니다.")
        return

    with st.spinner("관상을 살펴보는 중..."):
        st.session_state["analysis_count"] = used + 1
        try:
            st.session_state["results"][cache_key] = analyze_face(jpeg_bytes, api_key, model)
        except Exception as e:
            st.error(describe_api_error(e, model))
            return
    st.success("풀이가 나왔습니다. 결과를 확인해 보세요.", icon="🔮")


def render_body(api_key: str, model: str) -> None:
    left, right = st.columns([2, 3], gap="large")
    cache = st.session_state.setdefault("results", {})
    cache_key = None

    with left:
        st.subheader("사진")
        image_file = get_image_input()

        jpeg_bytes = None
        if image_file is not None:
            try:
                jpeg_bytes = prepare_image(image_file.getvalue())
            except ImageError as e:
                st.error(str(e))

        if jpeg_bytes is not None:
            # 같은 사진·같은 모델이면 다시 API를 호출하지 않고 저장된 결과를 쓴다
            cache_key = hashlib.sha256(jpeg_bytes + model.encode()).hexdigest()
            # 모바일에서 스크롤 없이 누를 수 있도록 버튼을 미리보기보다 위에 둔다
            if st.button("🔮 관상 보기", type="primary", width="stretch", key="analyze"):
                if cache_key not in cache:
                    # 진행 상황이 보이도록 버튼 바로 아래에서 실행한다
                    run_analysis(jpeg_bytes, cache_key, api_key, model)
            st.image(jpeg_bytes, width=PREVIEW_WIDTH)

        if image_file is not None:
            st.button(
                "다른 사진으로 다시 보기", width="stretch", on_click=reset, key="reset"
            )

    with right:
        st.subheader("관상 풀이")
        if cache_key in cache:
            render_result(cache[cache_key])
        else:
            render_empty_state()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    render_header()
    model = get_model()
    remaining = render_sidebar(model)
    api_key = load_api_key()
    render_body(api_key, model)
    render_remaining(remaining)  # 이번 실행의 분석까지 반영한 뒤 표시
    render_footer()


if __name__ == "__main__":
    main()
