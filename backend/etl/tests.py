from datetime import date

from django.test import SimpleTestCase, TestCase

from etl.services.transformer import PolicyTransformer, ZIPCD_TO_DISTRICT, _safe_replace_year

THIS_YEAR = date.today().year


class PolicyTransformerDateFixTests(SimpleTestCase):
    def setUp(self):
        self.transformer = PolicyTransformer()

    def test_parse_date_with_year_fix_minus2_to_current(self):
        parsed = self.transformer._parse_date_with_year_fix(f"{THIS_YEAR - 2}0916")
        self.assertEqual(parsed, date(THIS_YEAR, 9, 16))

    def test_parse_date_with_year_fix_minus1_to_current(self):
        parsed = self.transformer._parse_date_with_year_fix(f"{THIS_YEAR - 1}0630")
        self.assertEqual(parsed, date(THIS_YEAR, 6, 30))

    def test_parse_date_with_year_fix_current_unchanged(self):
        parsed = self.transformer._parse_date_with_year_fix(f"{THIS_YEAR}0101")
        self.assertEqual(parsed, date(THIS_YEAR, 1, 1))

    def test_parse_date_range_with_year_fix(self):
        start, end = self.transformer._parse_date_range_with_year_fix(
            f"{THIS_YEAR - 2}0916 ~ {THIS_YEAR - 1}1231"
        )
        self.assertEqual(start, date(THIS_YEAR, 9, 16))
        self.assertEqual(end, date(THIS_YEAR, 12, 31))

    def test_normalize_text_years(self):
        self.assertEqual(
            self.transformer._normalize_text_years(
                f"{THIS_YEAR - 2} 청년 {THIS_YEAR - 1} 지원"
            ),
            f"{THIS_YEAR} 청년 {THIS_YEAR} 지원"
        )

    def test_transform_keeps_policy_id_and_normalizes_text_fields(self):
        y2 = str(THIS_YEAR - 2)
        y1 = str(THIS_YEAR - 1)
        raw = {
            "plcyNo": "P-001",
            "plcyNm": f"{y2} 청년 일자리 정책",
            "plcyExplnCn": f"{y1}년 신청 가능",
            "plcySprtCn": f"{y2}~{y1} 지원금",
            "plcyAplyMthdCn": f"{y1} 온라인 신청",
            "aplyYmd": f"{y2}0916 ~ {y1}1231",
        }

        transformed = self.transformer.transform(raw)

        self.assertEqual(transformed.policy_id, "P-001")
        self.assertIn(str(THIS_YEAR), transformed.title)
        self.assertIn(str(THIS_YEAR), transformed.description)
        self.assertIn(str(THIS_YEAR), transformed.support_content)
        self.assertIn(str(THIS_YEAR), transformed.apply_method)

    def test_safe_replace_year_leap_day_falls_back_to_feb28(self):
        result = _safe_replace_year(date(2024, 2, 29), 2025)
        self.assertEqual(result, date(2025, 2, 28))


class PolicyTransformerDistrictTests(SimpleTestCase):
    def setUp(self):
        self.transformer = PolicyTransformer()

    def test_zipcd_to_district(self):
        self.assertEqual(self.transformer._parse_district('11380', ''), '은평구')

    def test_zipcd_gangnam(self):
        self.assertEqual(self.transformer._parse_district('11680', ''), '강남구')

    def test_zipcd_11000_returns_none(self):
        """11000은 서울시 전체 → 구 제한 없음(None)"""
        self.assertIsNone(self.transformer._parse_district('11000', ''))

    def test_zipcd_comma_multiple_returns_none(self):
        """쉼표 다중 코드 → 구 제한 없음(None)"""
        self.assertIsNone(self.transformer._parse_district('11380,11680', ''))

    def test_fallback_to_rgtr_inst(self):
        """zipCd 없으면 rgtrInstCdNm에서 추출"""
        self.assertEqual(
            self.transformer._parse_district('', '서울특별시 마포구'),
            '마포구'
        )

    def test_fallback_seoul_city_returns_none(self):
        self.assertIsNone(self.transformer._parse_district('', '서울특별시'))

    def test_both_empty_returns_none(self):
        self.assertIsNone(self.transformer._parse_district('', ''))

    def test_all_25_districts_mapped(self):
        """25개 구 코드가 전부 매핑되어 있는지"""
        self.assertEqual(len(ZIPCD_TO_DISTRICT), 25)


# =============================================================================
# [BRAIN4-37 C02] Override 적용 테스트
# =============================================================================
from unittest.mock import patch


class PolicyOverrideTests(SimpleTestCase):
    """override 적용/미적용 테스트"""

    def test_no_override_returns_unchanged(self):
        """override 없는 정책 → 값 불변"""
        from etl.services.overrides import apply_overrides
        fields = {'education_status': '0049009', 'employment_status': '0013009'}
        updated, logs = apply_overrides('NO_SUCH_POLICY', fields)
        self.assertEqual(updated, fields)
        self.assertEqual(logs, [])

    @patch.dict('etl.services.overrides.POLICY_FIELD_OVERRIDES', {
        'TEST_POLICY': {'education_status': '0049010'},
    }, clear=True)
    def test_override_applied(self):
        """override 있는 정책 → 기대값 반영"""
        from etl.services.overrides import apply_overrides
        fields = {'education_status': '0049009', 'employment_status': '0013009'}
        updated, logs = apply_overrides('TEST_POLICY', fields)
        self.assertEqual(updated['education_status'], '0049010')
        self.assertEqual(updated['employment_status'], '0013009')  # 변경 없음
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['before'], '0049009')
        self.assertEqual(logs[0]['after'], '0049010')

    @patch.dict('etl.services.overrides.POLICY_FIELD_OVERRIDES', {
        'TEST_POLICY': {'nonexistent_field': '0049010'},
    }, clear=True)
    def test_unknown_field_ignored_with_warning(self):
        """override에 존재하지 않는 field → 무시 + 로그"""
        from etl.services.overrides import apply_overrides
        fields = {'education_status': '0049009', 'employment_status': '0013009'}
        with self.assertLogs('etl.services.overrides', level='WARNING') as cm:
            updated, logs = apply_overrides('TEST_POLICY', fields)
        self.assertEqual(updated, fields)  # 값 불변
        self.assertEqual(logs, [])  # change log 없음
        self.assertIn('nonexistent_field', cm.output[0])  # 경고 로그에 필드명 포함


# =============================================================================
# [BRAIN4-37 C08] 결정표 64건 override 검증 테스트
# =============================================================================
from etl.services.overrides import POLICY_FIELD_OVERRIDES


class PolicyOverrideDecisionSheetTests(SimpleTestCase):
    """결정표 64건 override 정합성 검증"""

    def test_override_count_is_64(self):
        """override 정책 수 == 64"""
        self.assertEqual(len(POLICY_FIELD_OVERRIDES), 64)

    def test_all_fields_are_education_or_employment(self):
        """모든 override 필드가 education_status/employment_status만 포함"""
        allowed = {'education_status', 'employment_status'}
        for policy_id, fields in POLICY_FIELD_OVERRIDES.items():
            for field in fields:
                self.assertIn(
                    field, allowed,
                    f"{policy_id}: unexpected field '{field}'"
                )

    def test_no_unknown_codes_in_overrides(self):
        """unknown 코드(0049009/0013009) 미포함 확인"""
        for policy_id, fields in POLICY_FIELD_OVERRIDES.items():
            for field, value in fields.items():
                codes = {c.strip() for c in value.split(',')}
                self.assertNotIn(
                    '0049009', codes,
                    f"{policy_id}.{field} contains unknown edu code 0049009"
                )
                self.assertNotIn(
                    '0013009', codes,
                    f"{policy_id}.{field} contains unknown job code 0013009"
                )

    def test_dual_override_policy(self):
        """듀얼 override 정책(20250624005400111124) 검증"""
        entry = POLICY_FIELD_OVERRIDES.get('20250624005400111124')
        self.assertIsNotNone(entry)
        self.assertIn('education_status', entry)
        self.assertIn('employment_status', entry)
        self.assertEqual(
            entry['education_status'],
            '0049002,0049003,0049004,0049005,0049006,0049007,0049008',
        )
        self.assertEqual(entry['employment_status'], '0013001,0013003')

    def test_gap_unknown_merge_policy(self):
        """gap+unknown 병합 정책(20250113005400110180) 검증"""
        entry = POLICY_FIELD_OVERRIDES.get('20250113005400110180')
        self.assertIsNotNone(entry)
        self.assertEqual(
            entry['education_status'],
            '0049001,0049002,0049003,0049004,0049005,0049006,0049007,0049008',
        )


# =============================================================================
# [BRAIN4-43] 64건 override golden test (data-driven)
# =============================================================================
from etl.services.overrides import apply_overrides
from policies.services.matching_keys import KNOWN_EDUCATION_CODES, KNOWN_JOB_CODES


class PolicyOverrideGoldenTests(SimpleTestCase):
    """64건 override 데이터 순회, apply_overrides() 결과 검증"""

    def test_all_overrides_apply_successfully(self):
        """모든 override가 정상 적용되고, 결과가 known 코드만 포함"""
        for policy_id, overrides in POLICY_FIELD_OVERRIDES.items():
            # unknown 코드로 원본 구성 (override 전 상태 시뮬레이션)
            fields = {
                'education_status': '0049009',
                'employment_status': '0013009',
            }
            updated, logs = apply_overrides(policy_id, fields)

            for field, expected_value in overrides.items():
                self.assertEqual(
                    updated[field],
                    expected_value,
                    f"{policy_id}.{field}: expected {expected_value}, got {updated[field]}",
                )

                # 결과 코드가 모두 known인지 검증
                codes = {c.strip() for c in expected_value.split(',')}
                if field == 'education_status':
                    unknown = codes - KNOWN_EDUCATION_CODES
                else:
                    unknown = codes - KNOWN_JOB_CODES
                self.assertFalse(
                    unknown,
                    f"{policy_id}.{field}: unknown codes {unknown}",
                )


# =============================================================================
# [BRAIN4-45] _parse_int 버그 수정 테스트
# =============================================================================


class ParseIntTests(SimpleTestCase):
    def setUp(self):
        self.transformer = PolicyTransformer()

    def test_zero_string_returns_zero(self):
        self.assertEqual(self.transformer._parse_int('0'), 0)

    def test_zero_int_returns_zero(self):
        self.assertEqual(self.transformer._parse_int(0), 0)

    def test_none_returns_none(self):
        self.assertIsNone(self.transformer._parse_int(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.transformer._parse_int(''))

    def test_numeric_string(self):
        self.assertEqual(self.transformer._parse_int('3500'), 3500)

    def test_non_numeric_returns_none(self):
        self.assertIsNone(self.transformer._parse_int('abc'))


# =============================================================================
# [BRAIN4-45] 특수조건 필드 변환 테스트
# =============================================================================


class TransformerSpecialConditionTests(SimpleTestCase):
    def setUp(self):
        self.transformer = PolicyTransformer()
        self.base_raw = {
            'plcyNo': 'TEST-001',
            'plcyNm': '테스트 정책',
            'plcyExplnCn': '설명',
            'plcySprtCn': '지원내용',
        }

    def test_sbiz_cd_preserved(self):
        raw = {**self.base_raw, 'sbizCd': '0014001,0014003'}
        result = self.transformer.transform(raw)
        self.assertEqual(result.sbiz_cd, '0014001,0014003')

    def test_is_for_low_income(self):
        raw = {**self.base_raw, 'sbizCd': '0014001,0014003'}
        result = self.transformer.transform(raw)
        self.assertTrue(result.is_for_low_income)

    def test_is_for_single_parent(self):
        raw = {**self.base_raw, 'sbizCd': '0014004'}
        result = self.transformer.transform(raw)
        self.assertTrue(result.is_for_single_parent)

    def test_is_for_disabled(self):
        raw = {**self.base_raw, 'sbizCd': '0014005'}
        result = self.transformer.transform(raw)
        self.assertTrue(result.is_for_disabled)

    def test_no_sbiz_code_all_false(self):
        raw = {**self.base_raw, 'sbizCd': ''}
        result = self.transformer.transform(raw)
        self.assertFalse(result.is_for_low_income)
        self.assertFalse(result.is_for_single_parent)
        self.assertFalse(result.is_for_disabled)

    def test_sbiz_cd_none_no_error(self):
        raw = {**self.base_raw, 'sbizCd': None}
        result = self.transformer.transform(raw)
        self.assertEqual(result.sbiz_cd, '')
        self.assertFalse(result.is_for_low_income)

    def test_newlywed_exclusive_text(self):
        raw = {**self.base_raw, 'plcyExplnCn': '신혼부부 전용 주거 지원'}
        result = self.transformer.transform(raw)
        self.assertTrue(result.is_for_newlywed)

    def test_newlywed_inclusive_text(self):
        raw = {**self.base_raw, 'plcyExplnCn': '신혼부부 우대 가능'}
        result = self.transformer.transform(raw)
        self.assertFalse(result.is_for_newlywed)

    def test_no_newlywed_keyword(self):
        raw = {**self.base_raw, 'plcyExplnCn': '일반 청년 정책'}
        result = self.transformer.transform(raw)
        self.assertFalse(result.is_for_newlywed)


# =============================================================================
# [BRAIN4-45] Loader 특수조건 필드 DB 적재 테스트
# =============================================================================
from etl.services.loader import PolicyLoader
from etl.services.transformer import TransformedPolicy
from policies.models import Policy


class LoaderSpecialConditionTests(TestCase):
    def test_special_condition_fields_saved_to_db(self):
        policy = TransformedPolicy(
            policy_id='LOADER-TEST-001',
            title='테스트',
            description='설명',
            support_content='지원',
            age_min=19,
            age_max=39,
            income_level='',
            income_min=None,
            income_max=None,
            marriage_status='',
            employment_status='',
            education_status='',
            apply_start_date=None,
            apply_end_date=None,
            business_start_date=None,
            business_end_date=None,
            apply_method='',
            apply_url='',
            district=None,
            category='일자리',
            subcategory='',
            sbiz_cd='0014003,0014005',
            is_for_single_parent=False,
            is_for_disabled=True,
            is_for_low_income=True,
            is_for_newlywed=False,
            created_at=None,
            updated_at=None,
        )
        loader = PolicyLoader()
        loader.load([policy])

        saved = Policy.objects.get(policy_id='LOADER-TEST-001')
        self.assertEqual(saved.sbiz_cd, '0014003,0014005')
        self.assertTrue(saved.is_for_low_income)
        self.assertTrue(saved.is_for_disabled)
        self.assertFalse(saved.is_for_single_parent)
        self.assertFalse(saved.is_for_newlywed)
