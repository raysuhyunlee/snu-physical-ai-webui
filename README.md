# SNU Physical AI WebUI

[Open WebUI](https://github.com/open-webui/open-webui) 기반의 커스텀 버전입니다.

## 설치

도커 이미지를 이용해 한 줄의 커맨드로 설치 및 실행됩니다.

```sh
sh run.sh
```

---

## 환경 설정 (설치 후 1회만 수행)

관리자 계정으로 로그인 → **Admin Panel → Settings**

필요한 API 키:

| 기능 | 키 발급처 |
|------|-----------|
| Gemini (채팅 / 이미지) | [Google AI Studio](https://aistudio.google.com/apikey) |
| Mureka (음악) | [Mureka](https://www.mureka.ai/) |

---

### 1. 채팅 모델 설정 — Gemini `gemini-2.5-flash`

Gemini 채팅 모델은 **OpenAI 호환(OpenAI-compatible) 연결**로 추가합니다.

**Admin Panel → Settings → Connections → OpenAI API** 에서 연결 추가:

- **API Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai/`
- **API Key**: Google AI Studio 키
- 저장 후 모델 목록에서 메인으로 사용될 모델 (예: `gemini-2.5-flash`) 선택

---

### 2. 이미지 생성 설정 — Gemini `gemini-3-pro-image-preview`

**Admin Panel → Settings → Images** 에서:

| 항목 | 값 |
|------|-----|
| Image Generation | **활성화(Enable)** |
| Image Generation Engine | `gemini` |
| Gemini API Base URL | `https://generativelanguage.googleapis.com/v1beta` |
| Gemini API Key | Google AI Studio 키 |
| Endpoint Method | `generateContent` |
| Model | `gemini-3-pro-image-preview` |

> **주의**: Gemini 이미지 모델(`gemini-*-image-*`)은 `generateContent` 방식을 사용합니다. 구형 Imagen(`imagen-*`) 계열은 `predict` 방식입니다. 모델과 Endpoint Method를 반드시 맞춰야 합니다.

---

### 3. 음악 생성 설정 — Mureka

**Admin Panel → Settings → Music** 에서:

| 항목 | 값 |
|------|-----|
| Music Generation | **활성화(Enable)** |
| Engine | `mureka` |
| Mureka API Base URL | `https://api.mureka.ai/v1` |
| Mureka API Key | Mureka 키 |
| Model | `auto` (기본값) |

생성 요청은 Mureka의 `/song/generate` 엔드포인트로 전달됩니다.

---

### 4. 강의(Course) 설정

각 강의는 **Knowledge 컬렉션**과 1:1로 연결되어, 해당 강의 자료를 기반으로 한 RAG 질의응답을 제공합니다.

**강의 만들기**

1. 관리자 계정으로 로그인
2. **Admin Panel → Courses** (`/admin/courses`) 이동
3. **강의 생성** — 강의 이름 입력 시 동일 이름의 Knowledge 컬렉션이 자동 생성됨
4. 생성된 강의에 강의 자료 파일을 업로드 (RAG 인덱싱)

**사용**

- 상단 바의 **강의 선택기(Course Selector)** 에서 강의를 고르면, 이후 채팅이 해당 강의 자료를 컨텍스트로 사용
- 강의 수정/삭제는 관리자만 가능, 조회는 인증된 사용자 누구나 가능

---

### 참고

- 모든 설정값은 DB(PersistentConfig)에 저장되어 재시작 후에도 유지됩니다.
- 업스트림 Open WebUI 문서: <https://docs.openwebui.com/>
