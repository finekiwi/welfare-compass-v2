"""
임베딩/리트리버/리랭커 설정 통합 모듈

경로, 로깅, 리트리버, 리랭커, 평가 설정을 중앙 관리

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 빠른 설정 가이드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 경로 변경하기:
    → PathConfig 클래스의 상수 수정

📊 테스트 데이터 변경:
    PathConfig.DEFAULT_TEST_FILE = PROJECT_ROOT / "your/path/data.json"

💾 결과 저장 위치 변경:
    PathConfig.RERANKER_TEST_ROOT = PROJECT_ROOT / "your/results/dir"

🎯 리랭커 기본값 변경:
    RerankerConfig.DEFAULT_TYPE = "ko-reranker"  # "none" | "cohere" | ...

🔍 리트리버 가중치 조정:
    RetrieverConfig.DEFAULT_BM25_WEIGHT = 0.5
    RetrieverConfig.DEFAULT_DENSE_WEIGHT = 0.5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

설정 확인:
    python llm/embeddings/config.py
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Literal, FrozenSet, Dict, Optional


# ============================================================================
# 타입 정의
# ============================================================================
RerankerType = Literal["none", "cohere", "ko-reranker", "bge-reranker-v2-m3"]


# ============================================================================
# 경로 설정
# ============================================================================
class PathConfig:
    """프로젝트 경로 설정

    ⚙️  여기서 모든 경로를 수정하세요!
    """

    # ========================================
    # 🗂️ 프로젝트 루트 (자동 감지)
    # ========================================
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent  # /home/dydwn/projects/4brain-welfare

    # ========================================
    # 📊 테스트 데이터 경로
    # ========================================
    # 테스트 데이터가 있는 디렉토리
    TEST_DATA_DIR: Path = PROJECT_ROOT / "test" / "retriever_test"

    # 기본 테스트 데이터셋 (150개)
    DEFAULT_TEST_FILE: Path = PROJECT_ROOT / "data" / "processed" / "test_dataset_final_150.json"

    # 추가 테스트 데이터셋
    TEST_JOBS_FILE: Path = TEST_DATA_DIR / "test_data_jobs.json"  # 일자리 50개

    # ========================================
    # 💾 결과 저장 경로 (리랭커 테스트)
    # ========================================
    # 리랭커 테스트 결과 루트
    RERANKER_TEST_ROOT: Path = PROJECT_ROOT / "test" / "reranker_test"

    # 로그 저장 디렉토리
    LOG_DIR: Path = RERANKER_TEST_ROOT / "logs"

    # 결과 JSON 저장 디렉토리
    RESULTS_DIR: Path = RERANKER_TEST_ROOT / "results"

    @classmethod
    def ensure_dirs(cls) -> None:
        """필요한 디렉토리 생성"""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_log_path(cls, prefix: str = "eval", ext: str = "log") -> Path:
        """타임스탬프 기반 로그 파일 경로 생성"""
        cls.ensure_dirs()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return cls.LOG_DIR / f"{prefix}_{timestamp}.{ext}"

    @classmethod
    def get_result_path(cls, prefix: str = "result", ext: str = "json") -> Path:
        """타임스탬프 기반 결과 파일 경로 생성"""
        cls.ensure_dirs()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return cls.RESULTS_DIR / f"{prefix}_{timestamp}.{ext}"

    @classmethod
    def resolve(cls, path: Optional[str]) -> Path:
        """상대경로를 절대경로로 변환 (현재 디렉토리 또는 프로젝트 루트 기준)"""
        if path is None:
            return cls.DEFAULT_TEST_FILE

        p = Path(path)

        # 절대 경로면 그대로 반환
        if p.is_absolute():
            return p

        # 상대 경로면 현재 디렉토리 기준으로 먼저 확인
        cwd_path = Path.cwd() / p
        if cwd_path.exists():
            return cwd_path

        # 현재 디렉토리에 없으면 프로젝트 루트 기준
        return cls.PROJECT_ROOT / p

    @classmethod
    def get_test_file(cls, preset: str = "default") -> Path:
        """프리셋으로 테스트 파일 선택

        Args:
            preset: "default" (150개) | "jobs" (일자리 50개)
        """
        if preset == "jobs":
            return cls.TEST_JOBS_FILE
        return cls.DEFAULT_TEST_FILE

    @classmethod
    def list_available_tests(cls) -> Dict[str, Path]:
        """사용 가능한 테스트 데이터셋 목록"""
        tests = {
            "default": cls.DEFAULT_TEST_FILE,
            "jobs": cls.TEST_JOBS_FILE,
        }
        # 추가 파일 스캔
        if cls.TEST_DATA_DIR.exists():
            for f in cls.TEST_DATA_DIR.glob("*.json"):
                if f.stem not in tests:
                    tests[f.stem] = f
        return tests


# ============================================================================
# 로깅 설정
# ============================================================================
class LogConfig:
    """로깅 설정"""

    # 로그 포맷
    DATE_FORMAT: str = "%Y%m%d_%H%M%S"
    LOG_FORMAT: str = "[{timestamp}] {level}: {message}"

    # 로그 레벨
    VERBOSE: bool = True

    # 콘솔 출력 이모지
    EMOJI = {
        "success": "🟢",
        "fail": "🔴",
        "warning": "⚠️",
        "info": "📋",
        "search": "🔍",
        "rerank": "🎯",
        "time": "⏱️",
        "save": "💾",
        "load": "📂",
    }

    @classmethod
    def log(cls, message: str, level: str = "info", file=None) -> None:
        """로그 출력 (콘솔 + 파일)"""
        timestamp = datetime.now().strftime(cls.DATE_FORMAT)
        formatted = cls.LOG_FORMAT.format(timestamp=timestamp, level=level.upper(), message=message)

        if cls.VERBOSE:
            print(message)

        if file:
            file.write(message + "\n")
            file.flush()


# ============================================================================
# 리트리버 설정
# ============================================================================
class RetrieverConfig:
    """앙상블 리트리버 설정"""

    # 가중치
    DEFAULT_BM25_WEIGHT: float = 0.4
    DEFAULT_DENSE_WEIGHT: float = 0.6

    # 검색 개수 (팀원 버전 호환)
    ENSEMBLE_FETCH_K: int = 20  # 1차 검색에서 가져올 개수
    RERANK_TOP_K: int = 10      # 리랭킹 후 최종 반환 개수

    # 기본값 (ensemble_retriever.py와 evaluate_retriever.py에서 사용)
    DEFAULT_RETRIEVE_K: int = ENSEMBLE_FETCH_K  # 20
    DEFAULT_RERANK_K: int = ENSEMBLE_FETCH_K    # 20
    DEFAULT_TOP_K: int = RERANK_TOP_K           # 10


# ============================================================================
# 리랭커 설정
# ============================================================================
class RerankerConfig:
    """리랭커 설정"""
    
    # 허용된 리랭커 타입
    VALID_TYPES: FrozenSet[str] = frozenset([
        "none",
        "cohere",
        "ko-reranker",
        "bge-reranker-v2-m3",
    ])

    # 기본값: RERANKER_TYPE 환경변수로 재정의 가능 (기본값: cohere)
    DEFAULT_TYPE: RerankerType = os.getenv("RERANKER_TYPE", "cohere")
    DEFAULT_TOP_K: int = 10
    DEFAULT_MAX_LENGTH: int = 1024
    WARMUP_RUNS: int = 3
    
    # Cohere 설정
    COHERE_MODEL: str = "rerank-multilingual-v3.0"

    # Cohere Retry 설정
    COHERE_MAX_RETRIES: int = 5
    COHERE_BASE_DELAY: int = 1  # 초기 대기 시간 (초)
    COHERE_MAX_DELAY: int = 16  # 최대 대기 시간 (초)

    # 로컬 모델 매핑
    LOCAL_MODELS: Dict[str, str] = {
        "ko-reranker": "Dongjin-kr/ko-reranker",
        "bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
    }

    # 모델별 최적 설정
    MODEL_CONFIG: Dict[str, Dict] = {
        "ko-reranker": {
            "max_length": 512,
            "batch_size": 32,
        },
        "bge-reranker-v2-m3": {
            "max_length": 8192,
            "batch_size": 16,
        },
    }
    
    @classmethod
    def is_valid(cls, reranker_type: str) -> bool:
        return reranker_type in cls.VALID_TYPES
    
    @classmethod
    def is_local(cls, reranker_type: str) -> bool:
        return reranker_type in cls.LOCAL_MODELS
    
    @classmethod
    def get_model_name(cls, reranker_type: str) -> str:
        if reranker_type not in cls.LOCAL_MODELS:
            raise ValueError(f"Unknown local reranker: {reranker_type}")
        return cls.LOCAL_MODELS[reranker_type]

    @classmethod
    def get_model_config(cls, reranker_type: str) -> Dict:
        """모델별 최적 설정 반환"""
        return cls.MODEL_CONFIG.get(reranker_type, {
            "max_length": cls.DEFAULT_MAX_LENGTH,
            "batch_size": 32,
        })


# ============================================================================
# 평가 설정
# ============================================================================
class EvalConfig:
    """평가 스크립트 설정"""

    # 평가 K값들
    K_VALUES = [1, 3, 5, 10, 20, 50]
    DEFAULT_TOP_K: int = 50

    # Rate limit 대응
    DEFAULT_DELAY: float = 0  # Cohere Trial은 6초 권장

    # 목표 지표 (준용 문서 기준)
    TARGETS = {
        "faq_hit@1": 0.80,
        "faq_hit@3": 0.95,
        "compare_both@10": 0.90,
        "explore_recall@50": 0.90,
        "duplicate_rate@10": 0.20,  # 미만
    }

    @classmethod
    def get_test_file(cls) -> Path:
        """기본 테스트 파일 경로"""
        return PathConfig.DEFAULT_TEST_FILE


# ============================================================================
# 편의 함수
# ============================================================================
def get_config_summary() -> str:
    """현재 설정 요약 출력"""
    lines = [
        "=" * 70,
        "📋 Configuration Summary",
        "=" * 70,
        "",
        "🗂️  프로젝트 경로",
        f"   Project Root: {PathConfig.PROJECT_ROOT}",
        "",
        "📊 테스트 데이터",
        f"   기본 데이터셋 (150개): {PathConfig.DEFAULT_TEST_FILE.name}",
        f"   일자리 데이터셋 (50개): {PathConfig.TEST_JOBS_FILE.name}",
        f"   데이터 디렉토리: {PathConfig.TEST_DATA_DIR}",
        "",
        "💾 결과 저장",
        f"   결과 루트: {PathConfig.RERANKER_TEST_ROOT}",
        f"   로그 디렉토리: {PathConfig.LOG_DIR}",
        f"   결과 JSON: {PathConfig.RESULTS_DIR}",
        "",
        "🔍 리트리버 설정",
        f"   BM25 가중치: {RetrieverConfig.DEFAULT_BM25_WEIGHT}",
        f"   Dense 가중치: {RetrieverConfig.DEFAULT_DENSE_WEIGHT}",
        f"   Fetch K: {RetrieverConfig.ENSEMBLE_FETCH_K}",
        f"   Rerank Top K: {RetrieverConfig.RERANK_TOP_K}",
        "",
        "🎯 리랭커 설정",
        f"   기본 리랭커: {RerankerConfig.DEFAULT_TYPE}",
        f"   지원 리랭커: {', '.join(RerankerConfig.VALID_TYPES)}",
        "",
        "=" * 70,
    ]
    return "\n".join(lines)


# ============================================================================
# 메인 (설정 확인용)
# ============================================================================
if __name__ == "__main__":
    print(get_config_summary())

    # 경로 존재 확인
    print("\n[Path Check]")
    print(f"  Project Root exists: {PathConfig.PROJECT_ROOT.exists()}")
    print(f"  Test File exists: {PathConfig.DEFAULT_TEST_FILE.exists()}")
    print(f"  Log Dir exists: {PathConfig.LOG_DIR.exists()}")

    # 디렉토리 생성 테스트
    PathConfig.ensure_dirs()
    print(f"\n[After ensure_dirs]")
    print(f"  Log Dir exists: {PathConfig.LOG_DIR.exists()}")
    print(f"  Results Dir exists: {PathConfig.RESULTS_DIR.exists()}")