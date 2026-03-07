"""DB 적재 서비스"""

import logging
from typing import NamedTuple
from django.db import transaction
from policies.models import Policy, Category
from .transformer import TransformedPolicy

logger = logging.getLogger(__name__)


class LoadResult(NamedTuple):
    created: int
    updated: int
    skipped: int
    errors: list[str]


class PolicyLoader:
    """정책 DB 적재 (UPSERT)"""

    # 대분류 5개 (원본 API)
    CATEGORY_MAPPING = {
        '일자리': '일자리',
        '주거': '주거',
        '교육': '교육',
        '복지문화': '복지문화',
        '참여권리': '참여권리',
    }

    # 나이 기본값 (빈 값일 때)
    DEFAULT_MIN_AGE = 0
    DEFAULT_MAX_AGE = 99

    def __init__(self):
        self._category_cache: dict[str, Category] = {}
        self._init_categories()

    def _init_categories(self):
        category_names = list(self.CATEGORY_MAPPING.values()) + ['기타']
        for name in category_names:
            cat, created = Category.objects.get_or_create(name=name)
            self._category_cache[name] = cat

    @transaction.atomic
    def load(self, policies: list[TransformedPolicy]) -> LoadResult:
        created = 0
        updated = 0
        skipped = 0
        errors = []

        for policy in policies:
            try:
                was_created = self._load_one(policy)
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                logger.error(f"적재 실패 ({policy.policy_id}): {e}")  # [RENAME] plcy_no → policy_id
                errors.append(policy.policy_id)  # [RENAME] plcy_no → policy_id
                skipped += 1

        logger.info(f"적재 완료: 생성 {created}, 수정 {updated}, 스킵 {skipped}")
        return LoadResult(created, updated, skipped, errors)

    def _load_one(self, policy: TransformedPolicy) -> bool:
        # 나이 기본값 적용 (빈 값일 때만, 0은 유지)
        min_age = policy.age_min  # [RENAME] sprt_trgt_min_age → age_min
        max_age = policy.age_max  # [RENAME] sprt_trgt_max_age → age_max

        if min_age is None:
            min_age = self.DEFAULT_MIN_AGE
        if max_age is None:
            max_age = self.DEFAULT_MAX_AGE

        obj, created = Policy.objects.update_or_create(
            policy_id=policy.policy_id,  # [RENAME] plcy_no → policy_id
            defaults={
                'title': policy.title,  # [RENAME] plcy_nm → title
                'description': policy.description,  # [RENAME] plcy_expln_cn → description
                'support_content': policy.support_content,  # [RENAME] plcy_sprt_cn → support_content
                'age_min': min_age,  # [RENAME] sprt_trgt_min_age → age_min
                'age_max': max_age,  # [RENAME] sprt_trgt_max_age → age_max
                'income_level': policy.income_level,  # [RENAME] earn_cnd_se_cd → income_level
                'income_min': policy.income_min,  # [RENAME] earn_min_amt → income_min
                'income_max': policy.income_max,  # [RENAME] earn_max_amt → income_max
                'marriage_status': policy.marriage_status,  # [RENAME] mrg_stts_cd → marriage_status
                'employment_status': policy.employment_status,  # [RENAME] job_cd → employment_status
                'education_status': policy.education_status,  # [RENAME] school_cd → education_status
                'apply_start_date': policy.apply_start_date,  # [RENAME] aply_start_dt → apply_start_date
                'apply_end_date': policy.apply_end_date,  # [RENAME] aply_end_dt → apply_end_date
                'business_start_date': policy.business_start_date,  # [RENAME] biz_prd_bgng_ymd → business_start_date
                'business_end_date': policy.business_end_date,  # [RENAME] biz_prd_end_ymd → business_end_date
                'apply_method': policy.apply_method,  # [RENAME] plcy_aply_mthd_cn → apply_method
                'apply_url': policy.apply_url,  # [RENAME] aply_url_addr → apply_url
                'district': policy.district,
                'category': policy.category,  # [RENAME] lclsf_nm → category (대분류)
                'subcategory': policy.subcategory,  # [RENAME] mclsf_nm → subcategory (중분류)
                'sbiz_cd': policy.sbiz_cd,
                'is_for_single_parent': policy.is_for_single_parent,
                'is_for_disabled': policy.is_for_disabled,
                'is_for_low_income': policy.is_for_low_income,
                'is_for_newlywed': policy.is_for_newlywed,
                'created_at': policy.created_at,  # [RENAME] frst_reg_dt → created_at
                'updated_at': policy.updated_at,  # [RENAME] last_mdfcn_dt → updated_at
            }
        )

        # 카테고리 연결 (대분류 기준)
        self._link_categories(obj, policy.category)  # [RENAME] lclsf_nm → category

        return created

    def _link_categories(self, policy_obj: Policy, category: str):  # [RENAME] lclsf_nm → category
        policy_obj.categories.clear()

        if not category:  # [RENAME] lclsf_nm → category
            policy_obj.categories.add(self._category_cache['기타'])
            return

        mapped_name = self.CATEGORY_MAPPING.get(category, '기타')  # [RENAME] lclsf_nm → category
        category_obj = self._category_cache.get(mapped_name)
        if category_obj:
            policy_obj.categories.add(category_obj)
