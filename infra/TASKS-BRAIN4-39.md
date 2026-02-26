# BRAIN4-39: MCP 서버 Docker Compose 인프라 구성

## 목표
개발 환경에서 `docker compose up` 한 번으로 전체 서비스(DB, Backend, MCP, Frontend, Langfuse)를
실행할 수 있는 통합 인프라를 구성한다.

---

## 현재 상태

| 항목 | 상태 |
|------|------|
| `docker-compose.yaml` (루트) | PostgreSQL만 있음 (welfare_db) |
| `infra/docker-compose.langfuse.yaml` | Langfuse 스택 별도 구성 완료 |
| Dockerfile | 없음 (backend, llm, frontend 모두) |
| MCP 서버 전송방식 | stdio (컨테이너 간 통신 불가) |
| 환경변수 | `.env`에 하드코딩, Docker용 분리 없음 |

---

## 태스크 목록

### Phase 1: Dockerfile 작성

#### 1-1. Backend (Django) Dockerfile
- **경로**: `backend/Dockerfile`
- **베이스**: `python:3.12-slim`
- **내용**:
  - `requirements.txt` 또는 `uv` 기반 의존성 설치
  - gunicorn으로 서빙 (개발용은 `runserver`도 가능)
  - `collectstatic`, `migrate` 엔트리포인트 스크립트
  - 포트: 8000
- **확인사항**:
  - `psycopg2-binary` → Docker에서는 `psycopg2` + `libpq-dev` 빌드 의존성 고려
  - `uv` 사용 시 multi-stage build로 이미지 경량화

#### 1-2. LLM/MCP 서버 Dockerfile
- **경로**: `llm/Dockerfile`
- **베이스**: `python:3.12-slim`
- **빌드 컨텍스트**: ⚠️ `pyproject.toml`이 **프로젝트 루트**에만 있음 (`llm/` 내부에 없음)
  - 방법 A: build context를 루트(`.`)로 설정, Dockerfile 경로를 `llm/Dockerfile`로 지정
  - 방법 B: 루트에 Dockerfile을 두고 `llm/` 코드만 복사
  - **권장**: 방법 A (compose에서 `build: { context: ., dockerfile: llm/Dockerfile }`)
- **내용**:
  - `uv sync` 기반 의존성 설치 (루트 `pyproject.toml` + `uv.lock` 복사)
  - ChromaDB persistent 볼륨 마운트 (`/app/data/chroma_db`)
  - MCP 서버 실행 엔트리포인트
- **핵심 결정사항**:
  - **MCP 전송방식 변경**: 현재 `stdio` → Docker 환경에서는 `sse` 또는 `streamable-http`로 변경 필요
  - `server.py`에서 `mcp.run(transport="sse", port=8001)` 등으로 수정
  - LangGraph 에이전트가 MCP 클라이언트로 네트워크 접속하도록 연동 변경

#### 1-3. Frontend (Next.js) Dockerfile
- **경로**: `frontend/Dockerfile`
- **베이스**: `node:20-alpine`
- **패키지 매니저**: ⚠️ `pnpm` 사용 (`pnpm-lock.yaml` 존재, `package-lock.json` 없음)
  - `npm ci` 아님 → `corepack enable && pnpm install --frozen-lockfile`
- **내용**:
  - multi-stage build (deps → build → runner)
  - `pnpm install --frozen-lockfile` → `pnpm build` → `pnpm start`
  - 포트: ⚠️ **3001** (langfuse-web이 3000 사용 중이므로 충돌 방지)
- **환경변수**: `NEXT_PUBLIC_API_BASE_URL` 등 빌드타임 주입

---

### Phase 2: Docker Compose 통합

#### 2-1. 루트 `docker-compose.yaml` 재구성
- **서비스 구성**:

```
services:
  db:           # PostgreSQL 15 (welfare DB)
  backend:      # Django API 서버 (:8000)
  mcp:          # MCP 서버 (:8001, SSE)
  frontend:     # Next.js (:3001) ⚠️ langfuse-web이 :3000 사용
```

- **네트워크**: `welfare-net` (bridge) — 전 서비스 공유
- **볼륨**:
  - `postgres_data` — DB 영속 저장소
  - `chroma_data` — ChromaDB 벡터 저장소
- **의존성 순서**:
  - `db` → `backend` (migrate 후 서빙)
  - `db` → `mcp` (ChromaDB + PostgreSQL 접근)
  - `backend`, `mcp` → `frontend` (API 의존)

#### 2-2. Langfuse 연동 (override 방식)
- `infra/docker-compose.langfuse.yaml`을 override로 사용:
  ```bash
  docker compose -f docker-compose.yaml -f infra/docker-compose.langfuse.yaml up
  ```
- 또는 `docker-compose.override.yaml`로 개발 시 자동 포함
- Langfuse 네트워크를 `welfare-net`에 합류시킬지 별도 유지할지 결정

---

### Phase 3: 환경변수 정리

#### 3-1. `.env.docker` 파일 생성
- Docker 전용 환경변수 분리 (기존 `.env`는 로컬 개발용 유지)
- ⚠️ **자동 로드 안 됨**: `docker compose`는 기본으로 `.env`만 읽음
  - 방법 A: `docker compose --env-file .env.docker up --build`
  - 방법 B: 각 서비스에 `env_file: [.env.docker]` 명시 (**권장** — 실행 커맨드 실수 방지)
- 항목:
  ```env
  # DB
  DB_HOST=db
  DB_PORT=5432
  DB_NAME=welfare
  DB_USER=welfare_user
  DB_PASSWORD=welfare1234

  # Django
  DJANGO_SECRET_KEY=<생성>
  DJANGO_DEBUG=True
  ALLOWED_HOSTS=backend,localhost
  CORS_ALLOWED_ORIGINS=http://localhost:3001
  CSRF_TRUSTED_ORIGINS=http://localhost:3001

  # MCP
  MCP_SERVER_URL=http://mcp:8001
  MCP_TRANSPORT=sse

  # API Keys (각자 로컬 .env에서 가져옴)
  YOUTH_API_KEY=
  OPENAI_API_KEY=
  COHERE_API_KEY=

  # Langfuse
  LANGFUSE_SECRET_KEY=
  LANGFUSE_PUBLIC_KEY=
  LANGFUSE_BASE_URL=http://langfuse-web:3000

  # Frontend
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  FRONTEND_PORT=3001
  ```
- `.gitignore`에 `.env.docker` 추가 (API 키 포함 시)

#### 3-2. Django settings 환경변수 확인
- `settings.py`가 이미 `os.environ.get`으로 DB 설정 읽고 있어서 호환됨
- 환경변수 지원 추가 필요 항목:
  - `ALLOWED_HOSTS` — 현재 빈 리스트 하드코딩 (`settings.py:42`)
  - `CORS_ALLOWED_ORIGINS` — 현재 `localhost:3000` 하드코딩 (`settings.py:191`)
  - `CSRF_TRUSTED_ORIGINS` — 현재 `localhost:3000` 하드코딩 (`settings.py:199`)
  - Docker 환경에서는 서비스명 기반 origin 추가 필요

#### 3-3. Langfuse compose 비밀값 외부화
- ⚠️ `docker-compose.langfuse.yaml`에 비밀값 하드코딩 존재:
  - `DATABASE_URL` (패스워드 포함, line 18)
  - `ENCRYPTION_KEY` (line 20)
  - `NEXTAUTH_SECRET` (line 57)
  - Redis/MinIO/ClickHouse 패스워드들
- `.env.langfuse`로 분리하고 compose에서 `${VAR}` 참조로 변경

---

### Phase 4: MCP 연동 변경

#### 4-1. MCP 서버 전송방식 분기
- **파일**: `llm/mcp/server.py`
- `MCP_TRANSPORT` 환경변수로 `stdio` / `sse` 분기:
  ```python
  transport = os.getenv("MCP_TRANSPORT", "stdio")
  if transport == "sse":
      mcp.run(transport="sse", host="0.0.0.0", port=8001)
  else:
      mcp.run(transport="stdio")
  ```
- 로컬 개발: stdio 유지 (Claude Desktop, IDE 연동)
- Docker: sse로 네트워크 통신

#### 4-2. LangGraph 에이전트 MCP 클라이언트 설정
- **파일**: `llm/agents/agent.py`
- MCP 클라이언트가 `MCP_SERVER_URL` 환경변수로 접속
- stdio 모드일 때는 subprocess, sse 모드일 때는 HTTP 클라이언트로 분기

---

### Phase 5: 엔트리포인트 & 헬스체크

#### 5-1. Backend 엔트리포인트 스크립트
- **경로**: `backend/entrypoint.sh`
- DB 준비 대기 → migrate → collectstatic → gunicorn 기동
- ⚠️ **collectstatic 사전조건**: `STATIC_ROOT` 설정 필요 (`settings.py:158`에 `STATIC_URL`만 있고 `STATIC_ROOT` 없음)
  - `STATIC_ROOT = BASE_DIR / 'staticfiles'` 추가 필요 (없으면 collectstatic 실패)
- ⚠️ 헬스체크: `GET /api/health/` — **현재 라우트 없음** (`urls.py`에 미등록)
  - 간단한 헬스 뷰 추가 필요 (DB 연결 확인 포함)
  - `urls.py`에 path 등록 + view 함수 작성

#### 5-2. MCP 서버 헬스체크
- SSE 모드 시 `/sse` 엔드포인트 응답 확인
- `depends_on` + `healthcheck`로 순서 보장

#### 5-3. Frontend 헬스체크
- `curl http://localhost:3001` 응답 확인

---

### Phase 6: 테스트 & 문서

#### 6-1. 로컬 동작 검증
- [ ] `docker compose up --build` 정상 기동
- [ ] DB 마이그레이션 자동 실행
- [ ] Backend API 호출 (`http://localhost:8000/api/policies/`)
- [ ] MCP 서버 SSE 접속 (`http://localhost:8001/sse`)
- [ ] Frontend 페이지 로드 (`http://localhost:3001`)
- [ ] MCP ↔ LangGraph 에이전트 연동 (정책 검색 테스트)
  - ⚠️ **현재 chat send는 더미 응답** (`views.py:129` TODO 상태). 실제 LLM 연동은 별도 티켓.
  - 이번 PR에서는 MCP SSE 엔드포인트 접속 가능 여부만 검증
  - 실제 엔드포인트: `POST /api/v1/chat/sessions/{id}/send/`

#### 6-2. README 업데이트
- Docker 환경 실행 방법 추가
- 환경변수 설정 가이드
- Langfuse 포함/미포함 실행 옵션 안내

---

## 우선순위 & 순서

```
Phase 1 (Dockerfile) → Phase 3 (환경변수) → Phase 2 (Compose 통합)
  → Phase 4 (MCP 연동) → Phase 5 (헬스체크) → Phase 6 (테스트)
```

Phase 1-3은 병렬 작업 가능. Phase 4는 MCP 서버 코드 변경이 필요하므로
LLM 파트 담당자와 협의 필요.

---

## 결정사항 (확정)

| # | 항목 | 결정 |
|---|------|------|
| 1 | MCP 전송방식 | **SSE** |
| 2 | Python 패키지 매니저 | **uv 유지** |
| 3 | Langfuse 포함 여부 | **별도 compose 파일 분리** (override) |
| 4 | Frontend | **compose에 서비스 자리만 잡아두고, Dockerfile은 프론트팀이 작성** |
| 5 | 스코프 | **dev 환경만 우선, prod는 후속 PR** |
