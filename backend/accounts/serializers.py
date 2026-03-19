from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from dj_rest_auth.registration.serializers import RegisterSerializer
from policies.serializers import PolicyListSerializer
from policies.services.matching_keys import VALID_SPECIAL_CONDITIONS
from .models import Profile, Scrap


class CustomRegisterSerializer(RegisterSerializer):
    """
    dj-rest-auth 회원가입 시 프로필 자동 생성을 위한 Serializer
    """
    email_notification_consent = serializers.BooleanField(required=False, default=False)

    def validate_email(self, email):
        """이메일 중복 확인"""
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return email

    def save(self, request):
        user = super().save(request)
        
        # 프로필 생성
        profile, created = Profile.objects.get_or_create(user=user)
        
        # 알림 동의 처리
        if self.data.get('email_notification_consent'):
            profile.email_notification_enabled = True
            profile.notification_email = user.email
            profile.save()
            
        return user


class UserSerializer(serializers.ModelSerializer):
    """회원가입용 Serializer"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "비밀번호가 일치하지 않습니다."}
            )
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


class ProfileSerializer(serializers.ModelSerializer):
    """프로필 조회/수정용 Serializer"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    age = serializers.ReadOnlyField()
    interests = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Profile.interests.field.related_model.objects.all(),
        required=False
    )
    interests_display = serializers.SerializerMethodField()
    field_choices = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'username', 'email',
            'birth_year', 'district', 'income_level', 'income_amount',
            'job_status', 'education_status', 'marriage_status',
            'housing_type', 'household_size',
            'has_children', 'children_ages',
            'special_conditions', 'needs',
            'interests', 'interests_display',
            'email_notification_enabled', 'notification_email',
            'age',
            'created_at', 'updated_at',
            'field_choices',
        ]
        read_only_fields = ['username', 'email', 'age', 'created_at', 'updated_at']
    
    def get_interests_display(self, obj):
        return list(obj.interests.values_list('name', flat=True))

    def get_field_choices(self, obj):
        def to_options(choices):
            return [{'value': k, 'label': v} for k, v in choices]

        return {
            'job_status': to_options(Profile.JOB_STATUS_CHOICES),
            'education_status': to_options(Profile.EDUCATION_STATUS_CHOICES),
            'marriage_status': to_options(Profile.MARRIAGE_STATUS_CHOICES),
            'housing_type': to_options(Profile.HOUSING_TYPE_CHOICES),
            'income_level': to_options(Profile.INCOME_LEVEL_CHOICES),
            'special_conditions': [{'value': v, 'label': v} for v in VALID_SPECIAL_CONDITIONS],
        }
    
    def validate_children_ages(self, value):
        """자녀 나이 유효성 검사"""
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError("자녀 나이는 리스트 형태여야 합니다.")
            for age in value:
                if not isinstance(age, int) or age < 0 or age > 30:
                    raise serializers.ValidationError("자녀 나이는 0-30 사이의 정수여야 합니다.")
        return value
    
    def validate_special_conditions(self, value):
        """
        특수조건 유효성 검사

        [BRAIN4-31] 변경사항:
        - '중소기업', '군인' 추가: API sbizCd에 해당 코드 존재
          - 0014001: 중소기업 (8개 정책)
          - 0014007: 군인 (8개 정책)
        - matching.py에서 sbiz_cd 필터링 시 사용
        """
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError("특수조건은 리스트 형태여야 합니다.")
            for cond in value:
                if cond not in VALID_SPECIAL_CONDITIONS:
                    raise serializers.ValidationError(
                        f"유효하지 않은 특수조건: {cond}. 가능한 값: {VALID_SPECIAL_CONDITIONS}"
                    )
        return value


class ProfilePreferencesSerializer(serializers.ModelSerializer):
    """정책 매칭 정보(비민감 필드) 수정 전용 Serializer"""
    interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Profile.interests.field.related_model.objects.all(),
        required=False
    )

    class Meta:
        model = Profile
        fields = [
            'birth_year', 'district', 'income_level', 'income_amount',
            'job_status', 'education_status', 'marriage_status',
            'housing_type', 'household_size',
            'has_children', 'children_ages',
            'special_conditions', 'needs',
            'interests',
        ]

    def validate_children_ages(self, value):
        """자녀 나이 유효성 검사"""
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError("자녀 나이는 리스트 형태여야 합니다.")
            for age in value:
                if not isinstance(age, int) or age < 0 or age > 30:
                    raise serializers.ValidationError("자녀 나이는 0-30 사이의 정수여야 합니다.")
        return value

    def validate_special_conditions(self, value):
        """
        특수조건 유효성 검사

        [BRAIN4-31] 변경사항:
        - '중소기업', '군인' 추가: API sbizCd에 해당 코드 존재
          - 0014001: 중소기업 (8개 정책)
          - 0014007: 군인 (8개 정책)
        - matching.py에서 sbiz_cd 필터링 시 사용
        """
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError("특수조건은 리스트 형태여야 합니다.")
            for cond in value:
                if cond not in VALID_SPECIAL_CONDITIONS:
                    raise serializers.ValidationError(
                        f"유효하지 않은 특수조건: {cond}. 가능한 값: {VALID_SPECIAL_CONDITIONS}"
                    )
        return value

class ScrapSerializer(serializers.ModelSerializer):
    policy = PolicyListSerializer(read_only=True)
    
    class Meta:
        model = Scrap
        fields = ['id', 'policy', 'created_at']
