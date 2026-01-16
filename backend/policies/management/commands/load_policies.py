import json
from datetime import datetime
from django.core.management.base import BaseCommand
from policies.models import Policy, Category


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
        
        # 정책 적재
        count = 0
        for item in policies:
            # district 파싱: "서울특별시 은평구" → "은평구"
            district = None
            rgtr_inst = item.get('rgtrInstCdNm', '')
            if rgtr_inst and rgtr_inst != '서울특별시':
                district = rgtr_inst.replace('서울특별시 ', '')
            
            # 신청기간 파싱: "20250916 ~ 20250926"
            aply_start_dt = None
            aply_end_dt = None
            aply_ymd = item.get('aplyYmd', '')
            if aply_ymd and '~' in aply_ymd:
                parts = aply_ymd.split('~')
                try:
                    start = parts[0].strip()
                    end = parts[1].strip()
                    if start:
                        aply_start_dt = datetime.strptime(start, '%Y%m%d').date()
                    if end:
                        aply_end_dt = datetime.strptime(end, '%Y%m%d').date()
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
            
            # =================================================================
            # [BRAIN4-19] 사업기간 파싱 추가
            # =================================================================
            #
            # ❌ BEFORE: bizPrdBgngYmd, bizPrdEndYmd 필드 무시
            # - 원본 JSON에 있는데 파싱 안 함 → 달력에서 사업기간 표시 불가
            #
            # ✅ AFTER: "YYYYMMDD" → date 변환하여 DB 저장
            # - 프론트 달력의 mode='biz' 지원
            # =================================================================
            biz_prd_bgng_ymd = None
            biz_prd_end_ymd = None
            try:
                bgng = item.get('bizPrdBgngYmd', '')
                end = item.get('bizPrdEndYmd', '')
                if bgng and len(bgng) == 8:
                    biz_prd_bgng_ymd = datetime.strptime(bgng, '%Y%m%d').date()
                if end and len(end) == 8:
                    biz_prd_end_ymd = datetime.strptime(end, '%Y%m%d').date()
            except:
                pass
            
            # Policy 생성 또는 업데이트
            policy, created = Policy.objects.update_or_create(
                plcy_no=item['plcyNo'],
                defaults={
                    'plcy_nm': item.get('plcyNm', ''),
                    'plcy_expln_cn': item.get('plcyExplnCn', ''),
                    'plcy_sprt_cn': item.get('plcySprtCn', ''),
                    'sprt_trgt_min_age': min_age,
                    'sprt_trgt_max_age': max_age,
                    'sprt_trgt_age_lmt_yn': item.get('sprtTrgtAgeLmtYn', ''),
                    'earn_cnd_se_cd': item.get('earnCndSeCd', ''),
                    'earn_min_amt': int(item['earnMinAmt']) if item.get('earnMinAmt') and item['earnMinAmt'] != '' else None,
                    'earn_max_amt': int(item['earnMaxAmt']) if item.get('earnMaxAmt') and item['earnMaxAmt'] != '' else None,
                    'mrg_stts_cd': item.get('mrgSttsCd', ''),
                    'job_cd': item.get('jobCd', ''),
                    'school_cd': item.get('schoolCd', ''),
                    'aply_start_dt': aply_start_dt,
                    'aply_end_dt': aply_end_dt,
                    'plcy_aply_mthd_cn': item.get('plcyAplyMthdCn', ''),
                    'aply_url_addr': item.get('aplyUrlAddr', ''),
                    'district': district,
                    # [BRAIN4-19] 사업기간 필드
                    'biz_prd_bgng_ymd': biz_prd_bgng_ymd,
                    'biz_prd_end_ymd': biz_prd_end_ymd,
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
        
        self.stdout.write(self.style.SUCCESS(f'완료! 총 {count}개 정책 적재'))