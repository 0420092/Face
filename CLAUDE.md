# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

AI face-reading (관상) web app: the user uploads a face photo, an OpenAI vision model returns a Korean-language reading. All 4 stages of `PROMPTS.md` are done. `REVIEW.md` holds the stage 4 findings and, in section 7, how each was fixed and verified. The repo is `git init`-ed on `main` with no commits yet.

- `PRD.md` is the source of truth for requirements. Feature IDs (F-01 … F-24) and section numbers are referenced from prompts and reviews, so keep them stable when editing it.
- `PROMPTS.md` holds the planned 4-stage build: (1) skeleton, (2) features, (3) UI, (4) PRD review with Playwright. Check which stage the code is at before adding work from a later stage.

User-facing text, the system prompt, and model output are in Korean.

## Commands

```
pip install -r requirements.txt
streamlit run app.py
streamlit run app.py --server.headless true   # for Playwright testing at http://localhost:8501
```

No test suite or linter is set up yet; verification is done by running the app and driving it with Playwright (stage 4 in `PROMPTS.md`).

## Architecture (PRD section 7)

Single-file Streamlit app (`app.py`), deployed from GitHub to Streamlit Community Cloud.

- **Secrets come from two places.** Streamlit Cloud never sees `.env` (it is gitignored), so config is read through a `get_secret(key, default)` helper: `st.secrets` first, then `os.getenv` after `load_dotenv()`. Accessing `st.secrets` raises when no `secrets.toml` exists locally, so the lookup must be wrapped in try/except. Keys: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`; the model must support image input).
- **Image path:** upload or `st.camera_input` → size check (10MB) → Pillow `exif_transpose`, convert to RGB, resize long side to 1024px → JPEG → base64 data URL. Images stay in memory and are never written to disk. `Image.MAX_IMAGE_PIXELS` is lowered to 40M and `DecompressionBombWarning` is escalated to an error inside `prepare_image`; every failure there must surface as `ImageError` (an uncaught exception would otherwise blank the page).
- **Cost guard:** `run_analysis()` enforces a per-session API call cap (`MAX_ANALYSES_PER_SESSION`, default 10). It resets on page reload, so it is not a real budget control.
- **Input mode widget:** `st.segmented_control` uses the fixed key `"source"`; `reset()` and `keep_source_selected()` write to it from callbacks. Don't add a `default=` argument (it conflicts with setting the value via session state).
- **Model call:** OpenAI Chat Completions with an `image_url` content part and `max_completion_tokens=1500`. The installed SDK is openai 3.x; use `max_completion_tokens`, not `max_tokens` (newer models reject the latter). The system prompt fixes a 6-section markdown output (첫인상, 부위별 풀이, 운세, 성격, 조언, 종합 점수) and forbids appearance insults, sensitive-attribute guesses, and identifying real people. No face or multiple faces are signalled by sentinel replies (`NO_FACE`, `MULTIPLE_FACES`), detected by `classify_result()` via regex (tolerates backticks/punctuation/trailing text). The prompt explicitly allows paintings/illustrations and says to prefer a reading when unsure; without that, `gpt-4o-mini` misused the sentinels as an escape hatch.
- **State:** results are cached in `st.session_state["results"]` keyed by a hash of the processed image plus model name, so reruns don't call the API again. The reset button bumps `st.session_state["input_version"]`, which is part of every input widget's `key`; that is how the uploader/camera get cleared.
- **Result rendering** depends on the system prompt's format: `split_sections()` splits on `### ` headings and `SCORE_PATTERN` pulls the score from `**NN점**`. Changing the prompt's output format means updating these too; if the score isn't found, the section falls back to plain markdown.
- OpenAI errors (`AuthenticationError`, `RateLimitError`, `APIConnectionError`, `APIError`) and `PIL.UnidentifiedImageError` each get their own Korean message. A missing API key shows setup instructions and calls `st.stop()` rather than crashing.

## Notes

- Do not read or print `.env`; it holds the real API key.
- `.streamlit/config.toml` sets `server.maxUploadSize = 10`, which must match `MAX_FILE_MB` in `app.py` (camera input bypasses the uploader limit, so the code checks size too). Theme colors also go there; `.streamlit/secrets.toml` must stay gitignored.
- Port 8501 on this machine is used by another Streamlit app; run this one with `--server.port 8502`.
- Use Streamlit's `width="stretch"`, not the deprecated `use_container_width`.
- The disclaimer text in PRD section 9 must always be visible in the UI.
