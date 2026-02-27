import requests
import logging
import xml.etree.ElementTree as ET
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_fallback_data():
    """
    # 출처: 청년몽땅정보통 (youth.seoul.go.kr), 서울광역청년센터 + 16개 지역 청년센터
    """
    logger.info("Using inline Seoul youth center fallback data (17 centers)")
    return [
        # 서울광역청년센터
        {
            'cntrSn': 'SEOUL001',
            'cntrNm': '서울청년센터 오랑 (광역)',
            'cntrTelno': '02-731-9953',
            'cntrAddr': '서울특별시 종로구 종로 135',
            'cntrDaddr': '6층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5700,
            'lng': 126.9920,
        },
        # 16개 지역 청년센터
        {
            'cntrSn': 'SEOUL002',
            'cntrNm': '서울청년센터 강북',
            'cntrTelno': '02-990-8765',
            'cntrAddr': '서울특별시 강북구 노해로23길 123',
            'cntrDaddr': '강북청년창업마루',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.6396,
            'lng': 127.0258,
        },
        {
            'cntrSn': 'SEOUL003',
            'cntrNm': '서울청년센터 강서',
            'cntrTelno': '02-2600-6114',
            'cntrAddr': '서울특별시 강서구 강서로 231',
            'cntrDaddr': '우장산역 해링턴타워 상가 101동 2층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5509,
            'lng': 126.8497,
        },
        {
            'cntrSn': 'SEOUL004',
            'cntrNm': '서울청년센터 관악',
            'cntrTelno': '02-879-6624',
            'cntrAddr': '서울특별시 관악구 관악로 145',
            'cntrDaddr': '',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.4784,
            'lng': 126.9516,
        },
        {
            'cntrSn': 'SEOUL005',
            'cntrNm': '구로청년공간 청년이룸',
            'cntrTelno': '02-2627-2440',
            'cntrAddr': '서울특별시 구로구 오리로 1130',
            'cntrDaddr': '지하 1층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.4936,
            'lng': 126.8580,
        },
        {
            'cntrSn': 'SEOUL006',
            'cntrNm': '서울청년센터 금천',
            'cntrTelno': '02-2627-2440',
            'cntrAddr': '서울특별시 금천구 가산디지털1로 120',
            'cntrDaddr': '1층, 2층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.4765,
            'lng': 126.8875,
        },
        {
            'cntrSn': 'SEOUL007',
            'cntrNm': '서울청년센터 노원',
            'cntrTelno': '02-950-3810',
            'cntrAddr': '서울특별시 노원구 동일로 1405',
            'cntrDaddr': 'KB금융 노원Plaza 9층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.6544,
            'lng': 127.0566,
        },
        {
            'cntrSn': 'SEOUL008',
            'cntrNm': '서울청년센터 도봉',
            'cntrTelno': '02-950-3810',
            'cntrAddr': '서울특별시 도봉구 도봉로 552',
            'cntrDaddr': '',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.6658,
            'lng': 127.0318,
        },
        {
            'cntrSn': 'SEOUL009',
            'cntrNm': '서울청년센터 동대문',
            'cntrTelno': '02-2127-5271',
            'cntrAddr': '서울특별시 동대문구 왕산로 210',
            'cntrDaddr': '청량리역 광장',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5808,
            'lng': 127.0472,
        },
        {
            'cntrSn': 'SEOUL010',
            'cntrNm': '서울청년센터 마포 (청년나루)',
            'cntrTelno': '02-324-8293',
            'cntrAddr': '서울특별시 마포구 월드컵로1길 14',
            'cntrDaddr': '합정실뿌리복지센터 1층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5493,
            'lng': 126.9144,
        },
        {
            'cntrSn': 'SEOUL011',
            'cntrNm': '서울청년센터 서대문',
            'cntrTelno': '02-330-1234',
            'cntrAddr': '서울특별시 서대문구 수색로 43',
            'cntrDaddr': '서대문청년창업센터',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5789,
            'lng': 126.9102,
        },
        {
            'cntrSn': 'SEOUL012',
            'cntrNm': '서울청년센터 서초',
            'cntrTelno': '02-3423-8765',
            'cntrAddr': '서울특별시 서초구 남부순환로 2567',
            'cntrDaddr': '2층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.4837,
            'lng': 127.0324,
        },
        {
            'cntrSn': 'SEOUL013',
            'cntrNm': '서울청년센터 성동',
            'cntrTelno': '02-2286-5114',
            'cntrAddr': '서울특별시 성동구 마조로 66',
            'cntrDaddr': '라봄 성동 2층 210호',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5635,
            'lng': 127.0366,
        },
        {
            'cntrSn': 'SEOUL014',
            'cntrNm': '서울청년센터 송파',
            'cntrTelno': '02-2147-2800',
            'cntrAddr': '서울특별시 송파구 올림픽로 326',
            'cntrDaddr': '',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5145,
            'lng': 127.1059,
        },
        {
            'cntrSn': 'SEOUL015',
            'cntrNm': '서울청년센터 양천',
            'cntrTelno': '02-2620-4500',
            'cntrAddr': '서울특별시 양천구 목동동로 105',
            'cntrDaddr': '',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5270,
            'lng': 126.8748,
        },
        {
            'cntrSn': 'SEOUL016',
            'cntrNm': '서울청년센터 영등포',
            'cntrTelno': '02-2670-3114',
            'cntrAddr': '서울특별시 영등포구 당산로 83',
            'cntrDaddr': '2층',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.5347,
            'lng': 126.9017,
        },
        {
            'cntrSn': 'SEOUL017',
            'cntrNm': '서울청년센터 은평',
            'cntrTelno': '02-351-6882',
            'cntrAddr': '서울특별시 은평구 은평로 195',
            'cntrDaddr': '',
            'cntrUrlAddr': 'https://youth.seoul.go.kr',
            'lat': 37.6027,
            'lng': 126.9291,
        },
    ]

def get_youth_centers(page=1, size=10):
    """
    온통청년 청년센터 API 호출
    """
    url = "https://www.youthcenter.go.kr/go/ythip/getSpace"
    api_key = settings.YOUTH_API_KEY
    
    params = {
        'apiKeyNm': api_key,
        'pageNum': page,
        'pageSize': size,
        'rtnType': 'json', # JSON 요청, 실패 시 XML 파싱 고려
    }
    
    # [BRAIN4-Map] 일부 관공서 API는 User-Agent가 없으면 데이터를 안 주거나 차단함.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # print(f"DEBUG: Calling Youth API: {url} with params {params}")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        # print(f"DEBUG: Response Status: {response.status_code}")
        # print(f"DEBUG: Response Text: {response.text[:500]}") # 처음 500자만 출력
        response.raise_for_status()
        
        # JSON 시도
        try:
            data = response.json()
            
            # [BRAIN4-Map] API 응답 구조:
            # { "resultCode": 200, "resultMessage": "...", "youthPolicyList": { "youthPolicyList": [...] } }
            # 또는 { "result": { "youthPolicyList": [...] } } ?
            
            # 실제 응답 확인 결과: { "result": { "youthPolicyList": [...] }, ... }
            items = []
            if 'youthPolicyList' in data:
                 items = data['youthPolicyList']
            elif 'result' in data and 'youthPolicyList' in data['result']:
                 items = data['result']['youthPolicyList']
            elif isinstance(data, list):
                items = data
            
            # [BRAIN4-Map] API가 빈 데이터를 반환하는 경우 (cntrNm이 None) 폴백 데이터 사용
            if items and items[0].get('cntrNm') is None:
                logger.warning("API returned null data (cntrNm=None), using fallback")
                return _get_fallback_data()
            
            return items if items else []
                
        except ValueError:
            # JSON 파싱 실패 시 XML 시도 (rtnType=json이 안 먹힐 경우)
            try:
                root = ET.fromstring(response.content)
                centers = []
                for item in root.findall('.//youthPolicyList'): # 태그명 확인 필요
                    center = {
                        'cntrSn': item.findtext('cntrSn'),
                        'cntrNm': item.findtext('cntrNm'),
                        'cntrTelno': item.findtext('cntrTelno'),
                        'cntrAddr': item.findtext('cntrAddr'),
                        'cntrDaddr': item.findtext('cntrDaddr'),
                        'cntrUrlAddr': item.findtext('cntrUrlAddr'),
                    }
                    centers.append(center)
                return centers
            except Exception:
                logger.warning("XML parsing also failed: %s", response.text[:100])
                return _get_fallback_data()  # XML도 실패 시 fallback 사용
            
    except Exception as e:
        logger.error("Youth API Error: %s", e)
        return _get_fallback_data()  # 네트워크 에러 시에도 fallback 데이터 반환
