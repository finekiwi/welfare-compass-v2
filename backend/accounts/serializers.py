from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from policies.serializers import PolicyListSerializer
from .models import Profile, Scrap


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
            'age',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['username', 'email', 'age', 'created_at', 'updated_at']
    
    def get_interests_display(self, obj):
        return list(obj.interests.values_list('name', flat=True))
    
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
        """특수조건 유효성 검사"""
        valid_conditions = ['신혼', '한부모', '장애', '다자녀', '저소득', '차상위', '기초수급']
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError("특수조건은 리스트 형태여야 합니다.")
            for cond in value:
                if cond not in valid_conditions:
                    raise serializers.ValidationError(
                        f"유효하지 않은 특수조건: {cond}. 가능한 값: {valid_conditions}"
                    )
        return value

class ScrapSerializer(serializers.ModelSerializer):
    policy = PolicyListSerializer(read_only=True)
    
    class Meta:
        model = Scrap
        fields = ['id', 'policy', 'created_at']