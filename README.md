# 복지나침반

서울시 청년 복지정책 추천 AI 챗봇 서비스

## 팀 구성

| 이름 | 역할 |
|------|------|
| 심유나 | LLM & Agent |
| 권은영 | Frontend |
| 안준용 | Backend |

## 기술 스택

- Backend: Django 5.x, PostgreSQL
- Frontend: Next.js 14
- AI: LangGraph, OpenAI, Cohere

## 로컬 개발 환경 세팅

### 1. 저장소 클론
```bash
git clone https://github.com/팀/4brain-welfare.git
cd 4brain-welfare
```

### 2. Docker 실행
```bash
docker-compose up -d
```

### 3. Python 가상환경 및 패키지 설치
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 4. DB 마이그레이션
```bash
cd backend
python manage.py migrate
```

### 5. 데이터 적재
```bash
python manage.py run_etl
```

### 6. 서버 실행
```bash
python manage.py runserver
```

http://localhost:8000 접속
