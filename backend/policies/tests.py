from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import Profile
from policies.services.matching_keys import (
    MATCHING_DICT_KEYS,
    VALID_SPECIAL_CONDITIONS,
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

    def test_chatbot_top_k_is_2(self):
        self.assertEqual(CHATBOT_TOP_K, 2)


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
