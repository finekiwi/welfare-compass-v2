"""
온통청년 API 데이터를 DB에 적재하는 ETL 커맨드

[BRAIN4-14] 변경사항:
- sbizCd 파싱하여 특수조건 Boolean 필드 설정
- 신혼부부는 텍스트 파싱 (API 코드 없음)
"""
import json
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from policies.models import Policy, Category
from policies.services.matching_keys import (
    SBIZ_CODE_LOW_INCOME,
    SBIZ_CODE_SINGLE_PARENT,
    SBIZ_CODE_DISABLED,
)


# =============================================================================
# [BRAIN4-14] 신혼부부 "전용" 정책 판별 함수
# =============================================================================

def _is_newlywed_exclusive(policy_text: str) -> bool:
    """
    신혼부부 '전용' 정책인지 텍스트에서 판단
    (API에 신혼부부 코드가 없으므로 텍스트 파싱 필요)

    Returns:
        True: 신혼부부 전용 (비신혼부부 제외해야 함)
        False: 신혼부부 우대/가점 또는 해당없음 (모두 포함)
    """
    if '신혼' not in policy_text:
        return False

    # 포용적 표현 (이게 있으면 전용 아님 - 일반 청년도 지원 가능)
    inclusive_patterns = [
        '신혼부부 우대', '신혼부부 우선', '신혼부부 가점', '신혼부부 가산',
        '신혼부부도 가능', '신혼부부도 신청', '신혼부부도 지원',
        '신혼부부 포함', '신혼부부 해당자',
        '신혼부부인 경우 우대', '신혼부부인 경우 가점',
    ]

    for pattern in inclusive_patterns:
        if pattern in policy_text:
            return False

    # 배타적 표현 (이게 있으면 전용 - 신혼부부만 지원 가능)
    exclusive_patterns = [
        '신혼부부 전용', '신혼부부만 가능', '신혼부부만 신청',
        '신혼부부만 지원', '신혼부부에 한해', '신혼부부에 한함',
        '신혼부부에 한하여', '신혼부부 가구만',
    ]

    for pattern in exclusive_patterns:
        if pattern in policy_text:
            return True

    # 패턴 없으면 포용적으로 판단 (전용 아님)
    return False


class Command(BaseCommand):
    help = '온통청년 API 데이터를 DB에 적재'

    def handle(self, *args, **options):
        # JSON 파일 경로
        json_path = '../data/raw/seoul_policies.json'

        with open(json_path, 'r', encoding='utf-8') as f:
            policies = json.load(f)

        # 카테고리 미리 생성
        category_names = ['복지문화', '일자리', '교육', '주거', '참여권리', '기타']
        categories = {}
        for name in category_names:
            cat, _ = Category.objects.get_or_create(name=name)
            categories[name] = cat

        self.stdout.write(f'카테고리 {len(categories)}개 생성 완료')

        # [BRAIN4-14] 특수조건 통계 카운터
        stats = {
            'single_parent': 0,
            'disabled': 0,
            'low_income': 0,
            'newlywed': 0,
        }

        # 정책 적재
        count = 0
        for item in policies:
            # district 파싱: "서울특별시 은평구" → "은평구"
            district = None
            rgtr_inst = item.get('rgtrInstCdNm', '')
            if rgtr_inst and rgtr_inst != '서울특별시':
                district = rgtr_inst.replace('서울특별시 ', '')

            # 신청기간 파싱: "20250916 ~ 20250926"
            apply_start = None  # [RENAME] aply_start_dt → apply_start (로컬 변수)
            apply_end = None  # [RENAME] aply_end_dt → apply_end (로컬 변수)
            aply_ymd = item.get('aplyYmd', '')
            if aply_ymd and '~' in aply_ymd:
                parts = aply_ymd.split('~')
                try:
                    start = parts[0].strip()
                    end = parts[1].strip()
                    if start:
                        apply_start = datetime.strptime(start, '%Y%m%d').date()
                    if end:
                        apply_end = datetime.strptime(end, '%Y%m%d').date()
                except:
                    pass

            # 나이 파싱
            min_age = None
            max_age = None
            try:
                min_age_str = item.get('sprtTrgtMinAge', '')
                max_age_str = item.get('sprtTrgtMaxAge', '')
                if min_age_str and min_age_str != '0':
                    min_age = int(min_age_str)
                if max_age_str and max_age_str != '0':
                    max_age = int(max_age_str)
            except:
                pass

            # [BRAIN4-19] 사업기간 파싱
            biz_start = None  # [RENAME] biz_prd_bgng_ymd → biz_start (로컬 변수)
            biz_end = None  # [RENAME] biz_prd_end_ymd → biz_end (로컬 변수)
            try:
                bgng = item.get('bizPrdBgngYmd', '')
                end = item.get('bizPrdEndYmd', '')
                if bgng and len(bgng) == 8:
                    biz_start = datetime.strptime(bgng, '%Y%m%d').date()
                if end and len(end) == 8:
                    biz_end = datetime.strptime(end, '%Y%m%d').date()
            except:
                pass

            # [BRAIN4-14] 특수조건 파싱
            sbiz_cd = item.get('sbizCd', '')

            # sbizCd 기반 Boolean 설정
            is_for_single_parent = SBIZ_CODE_SINGLE_PARENT in sbiz_cd
            is_for_disabled = SBIZ_CODE_DISABLED in sbiz_cd
            is_for_low_income = SBIZ_CODE_LOW_INCOME in sbiz_cd

            # 신혼부부: 텍스트 파싱 (API 코드 없음)
            policy_text = f"{item.get('plcyExplnCn', '')} {item.get('plcySprtCn', '')}"
            is_for_newlywed = _is_newlywed_exclusive(policy_text)

            # 통계 업데이트
            if is_for_single_parent:
                stats['single_parent'] += 1
            if is_for_disabled:
                stats['disabled'] += 1
            if is_for_low_income:
                stats['low_income'] += 1
            if is_for_newlywed:
                stats['newlywed'] += 1

            # Policy 생성 또는 업데이트
            policy, created = Policy.objects.update_or_create(
                policy_id=item['plcyNo'],  # [RENAME] plcy_no → policy_id
                defaults={
                    'title': item.get('plcyNm', ''),  # [RENAME] plcy_nm → title
                    'description': item.get('plcyExplnCn', ''),  # [RENAME] plcy_expln_cn → description
                    'support_content': item.get('plcySprtCn', ''),  # [RENAME] plcy_sprt_cn → support_content
                    'age_min': min_age,  # [RENAME] sprt_trgt_min_age → age_min
                    'age_max': max_age,  # [RENAME] sprt_trgt_max_age → age_max
                    # [REMOVED] sprt_trgt_age_lmt_yn 삭제
                    'income_level': item.get('earnCndSeCd', ''),  # [RENAME] earn_cnd_se_cd → income_level
                    'income_min': int(item['earnMinAmt']) if item.get('earnMinAmt') and item['earnMinAmt'] != '' else None,  # [RENAME] earn_min_amt → income_min
                    'income_max': int(item['earnMaxAmt']) if item.get('earnMaxAmt') and item['earnMaxAmt'] != '' else None,  # [RENAME] earn_max_amt → income_max
                    'marriage_status': item.get('mrgSttsCd', ''),  # [RENAME] mrg_stts_cd → marriage_status
                    'employment_status': item.get('jobCd', ''),  # [RENAME] job_cd → employment_status
                    'education_status': item.get('schoolCd', ''),  # [RENAME] school_cd → education_status
                    'apply_start_date': apply_start,  # [RENAME] aply_start_dt → apply_start_date
                    'apply_end_date': apply_end,  # [RENAME] aply_end_dt → apply_end_date
                    'apply_method': item.get('plcyAplyMthdCn', ''),  # [RENAME] plcy_aply_mthd_cn → apply_method
                    'apply_url': item.get('aplyUrlAddr', ''),  # [RENAME] aply_url_addr → apply_url
                    'district': district,
                    # [BRAIN4-19] 사업기간 필드
                    'business_start_date': biz_start,  # [RENAME] biz_prd_bgng_ymd → business_start_date
                    'business_end_date': biz_end,  # [RENAME] biz_prd_end_ymd → business_end_date
                    # [BRAIN4-14] 특수조건 필드 (변경 없음)
                    'sbiz_cd': sbiz_cd,
                    'is_for_single_parent': is_for_single_parent,
                    'is_for_disabled': is_for_disabled,
                    'is_for_low_income': is_for_low_income,
                    'is_for_newlywed': is_for_newlywed,
                }
            )

            # 카테고리 연결 (M:N)
            lclsf = item.get('lclsfNm', '').strip()
            if lclsf:
                cat_names = [c.strip() for c in lclsf.split(',') if c.strip()]
            else:
                cat_names = ['기타']

            policy.categories.clear()
            for cat_name in cat_names:
                if cat_name in categories:
                    policy.categories.add(categories[cat_name])
                else:
                    policy.categories.add(categories['기타'])

            count += 1
            if count % 50 == 0:
                self.stdout.write(f'{count}개 처리 중...')

        # 완료 메시지 + 특수조건 통계
        self.stdout.write(self.style.SUCCESS(f'완료! 총 {count}개 정책 적재'))
        self.stdout.write(self.style.SUCCESS(
            f'[BRAIN4-14] 특수조건 정책 통계: '
            f'한부모={stats["single_parent"]}, '
            f'장애인={stats["disabled"]}, '
            f'기초수급={stats["low_income"]}, '
            f'신혼부부={stats["newlywed"]}'
        ))
