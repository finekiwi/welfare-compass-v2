"""
Data Migration: Django Sites 'example.com' -> 서비스 도메인으로 변경

allauth가 이메일 발송 시 Sites 테이블의 domain/name을 참조하므로,
기본값 'example.com'이 아닌 실제 서비스 정보로 변경합니다.
"""
from django.db import migrations


def update_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    site, created = Site.objects.get_or_create(id=1)
    site.domain = 'localhost:8000'  # 배포 시 실제 도메인으로 변경
    site.name = '복지나침반'
    site.save()


def reverse_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    site = Site.objects.get(id=1)
    site.domain = 'example.com'
    site.name = 'example.com'
    site.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_profile_education_status_and_more'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(update_site_domain, reverse_site_domain),
    ]
