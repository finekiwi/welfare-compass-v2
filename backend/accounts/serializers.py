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
    
    class Meta:
        model = Profile
        fields = [
            'username', 'email',
            'birth_year', 'district', 'income_level',
            'job_status', 'education_status', 'marriage_status',
            'interests', 'age',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['username', 'email', 'age', 'created_at', 'updated_at']

class ScrapSerializer(serializers.ModelSerializer):
    policy = PolicyListSerializer(read_only=True)
    
    class Meta:
        model = Scrap
        fields = ['id', 'policy', 'created_at']