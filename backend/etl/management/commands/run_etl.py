"""
ETL 실행 명령어

사용법:
    python manage.py run_etl                # 전체 (API → JSON → DB)
    python manage.py run_etl --fetch-only   # API → JSON 저장만
    python manage.py run_etl --load-only    # JSON → DB 적재만
    python manage.py run_etl --dry-run      # DB 저장 없이 테스트
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from etl.services.extractor import PolicyExtractor
from etl.services.transformer import PolicyTransformer
from etl.services.loader import PolicyLoader

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '온통청년 API → JSON → DB 적재 ETL 실행'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='DB 저장 없이 테스트')
        parser.add_argument('--fetch-only', action='store_true', help='API → JSON 저장만')
        parser.add_argument('--load-only', action='store_true', help='JSON → DB 적재만')
        parser.add_argument('--region', type=str, default='11000', help='지역코드 (기본: 서울)')
        parser.add_argument('--reindex', action='store_true', help='ETL 후 ChromaDB 재인덱싱')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fetch_only = options['fetch_only']
        load_only = options['load_only']
        region = options['region']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN 모드'))

        try:
            extractor = PolicyExtractor()

            # Step 1: Extract (API → JSON)
            if not load_only:
                self.stdout.write('1. API에서 데이터 수집 중...')
                json_path = extractor.fetch_and_save(region_code=region)
                self.stdout.write(f'   JSON 저장: {json_path}')
                
                if fetch_only:
                    self.stdout.write(self.style.SUCCESS('FETCH 완료 (--fetch-only)'))
                    return

            # Step 2: Transform (JSON → 정제)
            self.stdout.write('2. JSON에서 데이터 로드 및 정제 중...')
            raw = extractor.load_from_json()
            self.stdout.write(f'   로드: {len(raw)}개')

            transformer = PolicyTransformer()
            transformed = transformer.transform_many(raw)
            self.stdout.write(f'   정제: {len(transformed)}개')

            # Step 3: Load (정제 → DB)
            if dry_run:
                self.stdout.write('3. (DRY-RUN) DB 적재 스킵')
                self.stdout.write(self.style.SUCCESS('DRY-RUN 완료'))
                return

            self.stdout.write('3. DB 적재 중...')
            loader = PolicyLoader()
            result = loader.load(transformed)

            self.stdout.write(self.style.SUCCESS(
                f'ETL 완료: 생성 {result.created}, 수정 {result.updated}, 스킵 {result.skipped}'
            ))

            if options['reindex']:
                self.stdout.write('4. ChromaDB 재인덱싱 중...')
                from llm.embeddings.vector_store import create_vector_db
                create_vector_db(force_recreate=True)
                self.stdout.write(self.style.SUCCESS('   ChromaDB 재인덱싱 완료'))

        except Exception as e:
            logger.exception('ETL 실패')
            raise CommandError(f'ETL 실패: {e}')
