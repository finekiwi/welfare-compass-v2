# [BRAIN4-23] 필드명 한글약어 → 영문 변경 마이그레이션

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('policies', '0006_policy_lclsf_nm_policy_mclsf_nm'),
    ]

    operations = [
        # 기본 정보
        migrations.RenameField(model_name='policy', old_name='plcy_no', new_name='policy_id'),
        migrations.RenameField(model_name='policy', old_name='plcy_nm', new_name='title'),
        migrations.RenameField(model_name='policy', old_name='plcy_expln_cn', new_name='description'),
        migrations.RenameField(model_name='policy', old_name='plcy_sprt_cn', new_name='support_content'),

        # 자격 요건
        migrations.RenameField(model_name='policy', old_name='sprt_trgt_min_age', new_name='age_min'),
        migrations.RenameField(model_name='policy', old_name='sprt_trgt_max_age', new_name='age_max'),
        migrations.RenameField(model_name='policy', old_name='earn_cnd_se_cd', new_name='income_level'),
        migrations.RenameField(model_name='policy', old_name='earn_min_amt', new_name='income_min'),
        migrations.RenameField(model_name='policy', old_name='earn_max_amt', new_name='income_max'),
        migrations.RenameField(model_name='policy', old_name='mrg_stts_cd', new_name='marriage_status'),
        migrations.RenameField(model_name='policy', old_name='job_cd', new_name='employment_status'),
        migrations.RenameField(model_name='policy', old_name='school_cd', new_name='education_status'),

        # 신청 정보
        migrations.RenameField(model_name='policy', old_name='aply_start_dt', new_name='apply_start_date'),
        migrations.RenameField(model_name='policy', old_name='aply_end_dt', new_name='apply_end_date'),
        migrations.RenameField(model_name='policy', old_name='plcy_aply_mthd_cn', new_name='apply_method'),
        migrations.RenameField(model_name='policy', old_name='aply_url_addr', new_name='apply_url'),

        # 사업기간
        migrations.RenameField(model_name='policy', old_name='biz_prd_bgng_ymd', new_name='business_start_date'),
        migrations.RenameField(model_name='policy', old_name='biz_prd_end_ymd', new_name='business_end_date'),

        # 카테고리
        migrations.RenameField(model_name='policy', old_name='lclsf_nm', new_name='category'),
        migrations.RenameField(model_name='policy', old_name='mclsf_nm', new_name='subcategory'),

        # 메타
        migrations.RenameField(model_name='policy', old_name='frst_reg_dt', new_name='created_at'),
        migrations.RenameField(model_name='policy', old_name='last_mdfcn_dt', new_name='updated_at'),

        # sprt_trgt_age_lmt_yn 삭제
        migrations.RemoveField(model_name='policy', name='sprt_trgt_age_lmt_yn'),
    ]
