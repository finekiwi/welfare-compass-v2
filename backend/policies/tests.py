from unittest.mock import patch
from django.test import TestCase, SimpleTestCase
from django.contrib.auth.models import User
from accounts.models import Profile
from policies.services.matching import (
    match_policies_for_web,
    match_policies_for_chatbot,
    _select_diverse_categories,
    _passes_profile_code_filters,
)
from policies.services.matching_keys import (
    MATCHING_DICT_KEYS,
    CHATBOT_TOP_K,
    JOB_STATUS_TO_CODE,
    JOB_STATUS_TO_KOREAN,
    EDUCATION_STATUS_TO_CODE,
    MARRIAGE_STATUS_TO_CODE,
    HOUSING_TYPE_TO_KOREAN,
    normalize_special_conditions,
    normalize_user_info,
)


class TestNormalization(TestCase):
    """특수조건 alias 정규화 테스트"""

    def test_alias_장애인_to_장애(self):
        self.assertEqual(normalize_special_conditions(['장애인']), ['장애'])

    def test_alias_기초수급자_to_기초수급(self):
        self.assertEqual(normalize_special_conditions(['기초수급자']), ['기초수급'])

    def test_alias_수급자_to_기초수급(self):
        self.assertEqual(normalize_special_conditions(['수급자']), ['기초수급'])

    def test_canonical_unchanged(self):
        result = normalize_special_conditions(['신혼', '한부모', '장애'])
        self.assertEqual(result, ['신혼', '한부모', '장애'])

    def test_dedup_after_alias(self):
        result = normalize_special_conditions(['장애', '장애인'])
        self.assertEqual(result, ['장애'])

    def test_empty_list(self):
        self.assertEqual(normalize_special_conditions([]), [])

    def test_normalize_user_info(self):
        info = {'age': 25, 'special_conditions': ['장애인', '수급자']}
        result = normalize_user_info(info)
        self.assertEqual(result['special_conditions'], ['장애', '기초수급'])
        self.assertEqual(result['age'], 25)

    def test_normalize_user_info_no_mutation(self):
        """원본 dict를 변경하지 않는지 확인"""
        original = {'special_conditions': ['장애인']}
        normalize_user_info(original)
        self.assertEqual(original['special_conditions'], ['장애인'])

    def test_education_label_g3_to_expected_highschool_code(self):
        result = normalize_user_info({'education_code': '고3'})
        self.assertEqual(result['education_code'], '0049003')

    def test_education_label_d4_to_expected_university_code(self):
        result = normalize_user_info({'education_code': '대4'})
        self.assertEqual(result['education_code'], '0049006')

    def test_education_status_label_is_promoted_to_code(self):
        result = normalize_user_info({'education_status': '대4'})
        self.assertEqual(result['education_code'], '0049006')


class TestMatchingDictKeys(TestCase):
    """Profile.to_matching_dict() 키 집합 계약 테스트"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = self.user.profile

    def test_key_set_matches_contract(self):
        result = self.profile.to_matching_dict()
        self.assertEqual(set(result.keys()), MATCHING_DICT_KEYS)


class TestReturnPolicyContract(TestCase):
    """반환 계약 테스트"""

    def test_chatbot_top_k_is_5(self):
        self.assertEqual(CHATBOT_TOP_K, 5)


class TestCodeMappingCompleteness(TestCase):
    """모든 model CHOICES가 코드 매핑에 존재하는지 회귀 테스트"""

    def test_all_job_statuses_have_code(self):
        for value, label in Profile.JOB_STATUS_CHOICES:
            self.assertIn(value, JOB_STATUS_TO_CODE, f"Missing job code: {value}")

    def test_all_job_statuses_have_korean(self):
        for value, label in Profile.JOB_STATUS_CHOICES:
            self.assertIn(value, JOB_STATUS_TO_KOREAN, f"Missing korean: {value}")

    def test_all_education_statuses_have_code(self):
        for value, label in Profile.EDUCATION_STATUS_CHOICES:
            self.assertIn(value, EDUCATION_STATUS_TO_CODE, f"Missing edu code: {value}")

    def test_all_marriage_statuses_have_code(self):
        for value, label in Profile.MARRIAGE_STATUS_CHOICES:
            self.assertIn(value, MARRIAGE_STATUS_TO_CODE, f"Missing marriage code: {value}")

    def test_all_housing_types_have_korean(self):
        for value, label in Profile.HOUSING_TYPE_CHOICES:
            self.assertIn(value, HOUSING_TYPE_TO_KOREAN, f"Missing korean: {value}")


# =============================================================================
# [BRAIN4-37 C01] Known Code Registry 테스트
# =============================================================================
from policies.services.matching_keys import (
    KNOWN_EDUCATION_CODES,
    KNOWN_JOB_CODES,
    parse_code_string,
    has_unknown_codes,
    extract_known_only,
)


class TestParseCodeString(TestCase):
    """parse_code_string 유틸 테스트"""

    def test_comma_separated(self):
        self.assertEqual(parse_code_string('0013001, 0013003'), {'0013001', '0013003'})

    def test_none_returns_empty(self):
        self.assertEqual(parse_code_string(None), set())

    def test_empty_string_returns_empty(self):
        self.assertEqual(parse_code_string(''), set())

    def test_single_code(self):
        self.assertEqual(parse_code_string('0049010'), {'0049010'})

    def test_range_expression(self):
        result = parse_code_string('0013001~0013003')
        self.assertEqual(result, {'0013001', '0013002', '0013003'})


class TestHasUnknownCodes(TestCase):
    """has_unknown_codes 유틸 테스트"""

    def test_known_only_returns_false(self):
        self.assertFalse(has_unknown_codes('0013001,0013003', KNOWN_JOB_CODES))

    def test_unknown_present_returns_true(self):
        self.assertTrue(has_unknown_codes('0013001,0013009', KNOWN_JOB_CODES))

    def test_none_returns_false(self):
        self.assertFalse(has_unknown_codes(None, KNOWN_JOB_CODES))


class TestExtractKnownOnly(TestCase):
    """extract_known_only 유틸 테스트"""

    def test_removes_unknown(self):
        self.assertEqual(extract_known_only('0013001,0013009', KNOWN_JOB_CODES), '0013001')

    def test_all_known_unchanged(self):
        self.assertEqual(extract_known_only('0013001,0013003', KNOWN_JOB_CODES), '0013001,0013003')

    def test_all_unknown_returns_empty(self):
        self.assertEqual(extract_known_only('0013009', KNOWN_JOB_CODES), '')


class TestWebChatbotCategoryCapContract(SimpleTestCase):
    """[BRAIN4-37 C07] 웹/챗봇 카테고리 cap 계약 테스트"""

    class DummyProfile:
        def to_matching_dict(self):
            return {'age': 25}

    @patch('policies.services.matching._match_policies_core', return_value=[])
    def test_web_calls_core_with_no_category_cap(self, mock_core):
        profile = self.DummyProfile()
        match_policies_for_web(profile)

        mock_core.assert_called_once_with(
            {'age': 25},
            exclude_policy_ids=None,
            include_category=None,
            limit=None,
            max_per_category=None,
        )

    @patch('policies.services.matching._match_policies_core', return_value=[])
    def test_chatbot_calls_core_with_cap_2(self, mock_core):
        match_policies_for_chatbot({'age': 25})

        mock_core.assert_called_once_with(
            {'age': 25},
            exclude_policy_ids=None,
            include_category=None,
            limit=CHATBOT_TOP_K,
            max_per_category=2,
        )


class TestSelectDiverseCategories(SimpleTestCase):
    """[BRAIN4-37 C07] 카테고리 제한 동작 테스트"""

    class DummyPolicy:
        def __init__(self, subcategory, category):
            self.subcategory = subcategory
            self.category = category

    def test_no_cap_returns_all_scored_order(self):
        scored = [
            (self.DummyPolicy('주거', '주거'), 100),
            (self.DummyPolicy('주거', '주거'), 95),
            (self.DummyPolicy('주거', '주거'), 90),
            (self.DummyPolicy('일자리', '일자리'), 85),
        ]

        result = _select_diverse_categories(scored, max_per_category=None, limit=None)
        self.assertEqual(len(result), 4)
        self.assertEqual([score for _, score in result], [100, 95, 90, 85])

    def test_cap_2_limits_per_category(self):
        scored = [
            (self.DummyPolicy('주거', '주거'), 100),
            (self.DummyPolicy('주거', '주거'), 95),
            (self.DummyPolicy('주거', '주거'), 90),
            (self.DummyPolicy('일자리', '일자리'), 85),
        ]

        result = _select_diverse_categories(scored, max_per_category=2, limit=None)
        self.assertEqual(len(result), 3)
        self.assertEqual([score for _, score in result], [100, 95, 85])


class TestFailOpenGuard(SimpleTestCase):
    """[BRAIN4-37 C06] unknown 코드 fail-open 가드 테스트"""

    class DummyPolicy:
        def __init__(
            self,
            policy_id='P-001',
            employment_status='',
            education_status='',
            marriage_status='',
            income_level='',
            income_max=None,
        ):
            self.policy_id = policy_id
            self.employment_status = employment_status
            self.education_status = education_status
            self.marriage_status = marriage_status
            self.income_level = income_level
            self.income_max = income_max

    def test_job_unknown_only_passes(self):
        policy = self.DummyPolicy(employment_status='0013009')
        user = {'job_code': '0013001'}
        self.assertTrue(_passes_profile_code_filters(policy, user))

    def test_job_mixed_known_and_unknown_uses_known_only(self):
        policy = self.DummyPolicy(employment_status='0013003,0013009')
        self.assertFalse(_passes_profile_code_filters(policy, {'job_code': '0013001'}))
        self.assertTrue(_passes_profile_code_filters(policy, {'job_code': '0013003'}))

    def test_education_unknown_only_passes(self):
        policy = self.DummyPolicy(education_status='0049009')
        user = {'education_code': '0049007'}
        self.assertTrue(_passes_profile_code_filters(policy, user))

    def test_education_mixed_known_and_unknown_uses_known_only(self):
        policy = self.DummyPolicy(education_status='0049005,0049009')
        self.assertFalse(_passes_profile_code_filters(policy, {'education_code': '0049007'}))
        self.assertTrue(_passes_profile_code_filters(policy, {'education_code': '0049005'}))

    def test_education_also_match_is_respected(self):
        # 사용자 0049005(대학재학)는 0049006(대졸예정) 정책도 매칭되어야 함
        policy = self.DummyPolicy(education_status='0049006,0049009')
        self.assertTrue(_passes_profile_code_filters(policy, {'education_code': '0049005'}))

    def test_marriage_filter_kept(self):
        policy = self.DummyPolicy(marriage_status='0055001')  # 기혼 전용
        self.assertFalse(_passes_profile_code_filters(policy, {'marriage_code': '0055002'}))
        self.assertTrue(_passes_profile_code_filters(policy, {'marriage_code': '0055001'}))


# =============================================================================
# [BRAIN4-37] 소득 매칭 테스트
# =============================================================================
from policies.services.matching import (
    _matches_income_requirement,
    _annual_income_to_median_pct,
)


class TestIncomeMatching(SimpleTestCase):
    """소득 요건 매칭 테스트 (8개)"""

    class DummyPolicy:
        def __init__(self, income_level='', income_max=None):
            self.income_level = income_level
            self.income_max = income_max

    def test_income_any_passes(self):
        """0043001(무관) → pass"""
        policy = self.DummyPolicy(income_level='0043001')
        self.assertTrue(_matches_income_requirement(policy, {'income': 5000}))

    def test_income_annual_under_passes(self):
        """0043002(연소득) user < max → pass"""
        policy = self.DummyPolicy(income_level='0043002', income_max=5000)
        self.assertTrue(_matches_income_requirement(policy, {'income': 3000}))

    def test_income_annual_over_fails(self):
        """0043002(연소득) user > max → fail"""
        policy = self.DummyPolicy(income_level='0043002', income_max=5000)
        self.assertFalse(_matches_income_requirement(policy, {'income': 6000}))

    def test_income_annual_equal_passes(self):
        """0043002(연소득) user == max → pass"""
        policy = self.DummyPolicy(income_level='0043002', income_max=5000)
        self.assertTrue(_matches_income_requirement(policy, {'income': 5000}))

    def test_income_user_none_failopen(self):
        """user income 미입력 → fail-open (pass)"""
        policy = self.DummyPolicy(income_level='0043002', income_max=5000)
        self.assertTrue(_matches_income_requirement(policy, {}))

    def test_income_other_passes(self):
        """0043003(기타) → pass"""
        policy = self.DummyPolicy(income_level='0043003')
        self.assertTrue(_matches_income_requirement(policy, {'income': 5000}))

    def test_income_empty_passes(self):
        """빈값 → pass"""
        policy = self.DummyPolicy(income_level='')
        self.assertTrue(_matches_income_requirement(policy, {'income': 5000}))

    def test_income_unknown_code_passes(self):
        """알수없는 코드 → pass (fail-open)"""
        policy = self.DummyPolicy(income_level='0043999')
        self.assertTrue(_matches_income_requirement(policy, {'income': 5000}))


class TestIncomeMaxZeroFailopen(SimpleTestCase):
    """income_max=0 또는 None 가드 테스트"""

    class DummyPolicy:
        def __init__(self, income_level='', income_max=None):
            self.income_level = income_level
            self.income_max = income_max

    def test_income_annual_max_none_failopen(self):
        """0043002인데 income_max=None → fail-open"""
        policy = self.DummyPolicy(income_level='0043002', income_max=None)
        self.assertTrue(_matches_income_requirement(policy, {'income': 9999}))

    def test_income_annual_max_zero_failopen(self):
        """0043002인데 income_max=0 → fail-open"""
        policy = self.DummyPolicy(income_level='0043002', income_max=0)
        self.assertTrue(_matches_income_requirement(policy, {'income': 9999}))


class TestMedianIncomeConversion(SimpleTestCase):
    """중위소득 환산 테스트 (6개)"""

    def test_1person_100pct(self):
        """1인가구 연소득=중위소득 → 100%"""
        annual = 2_564_238 * 12 // 10_000  # 월→연→만원
        result = _annual_income_to_median_pct(annual, 1)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 100.0, delta=1.0)

    def test_4person_50pct(self):
        """4인가구 연소득=중위소득 50% → 50%"""
        annual_50pct = 6_509_816 * 12 // 10_000 // 2
        result = _annual_income_to_median_pct(annual_50pct, 4)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 50.0, delta=1.0)

    def test_none_annual_income(self):
        """연소득 None → None"""
        self.assertIsNone(_annual_income_to_median_pct(None, 4))

    def test_none_household_size(self):
        """가구원수 None → None"""
        self.assertIsNone(_annual_income_to_median_pct(3000, None))

    def test_household_7_capped_to_6(self):
        """가구원수 7 → 6인으로 cap"""
        result_7 = _annual_income_to_median_pct(5000, 7)
        result_6 = _annual_income_to_median_pct(5000, 6)
        self.assertEqual(result_7, result_6)

    def test_household_0_returns_none(self):
        """가구원수 0 → None"""
        self.assertIsNone(_annual_income_to_median_pct(3000, 0))
