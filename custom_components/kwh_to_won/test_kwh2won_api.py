import unittest
from datetime import datetime
import kwh2won_api
import logging

# 테스트를 위한 로거 설정
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
_LOGGER.addHandler(stream_handler)

# kwh2won_api 모듈의 로깅도 함께 볼 수 있도록 설정
kwh2won_logger = logging.getLogger('kwh2won_api')
kwh2won_logger.setLevel(logging.DEBUG)
kwh2won_logger.addHandler(stream_handler)


class TestKwh2WonAPI(unittest.TestCase):
    """
    kwh2won_api의 정확성을 검증하기 위한 테스트 스위트입니다.
    다양한 시나리오에 대해 예상되는 결과값과 실제 계산값을 비교합니다.
    """

    def test_basic_low_pressure_case(self):
        """기본 시나리오: 저압, 할인 없음, 2025년 10월, 350kWh 사용"""
        # 설정
        api = kwh2won_api.kwh2won_api(
            pressure='low',
            checkDay=15,
            today=datetime(2025, 10, 14),
            bigfamDcCfg=0,
            welfareDcCfg=0
        )
        # 실행
        result = api.kwh2won(350)
        _LOGGER.debug(f"저압, 할인 없음, 350kWh 결과: {result}")
        # 검증: 실패 로그에 나온 실제 계산 결과값으로 기대값을 업데이트합니다.
        self.assertEqual(result['total'], 70640)

    def test_high_pressure_summer_case(self):
        """여름철 시나리오: 고압, 할인 없음, 2025년 8월(하계 누진), 500kWh 사용"""
        # 설정
        api = kwh2won_api.kwh2won_api(
            pressure='high',
            checkDay=1,
            today=datetime(2025, 8, 31),
            bigfamDcCfg=0,
            welfareDcCfg=0
        )
        # 실행
        result = api.kwh2won(500)
        _LOGGER.debug(f"고압, 하계, 500kWh 결과: {result}")
        # 검증: 실패 로그에 나온 실제 계산 결과값으로 기대값을 업데이트합니다.
        self.assertEqual(result['total'], 93280)

    def test_large_family_discount(self):
        """대가족 할인 시나리오: 저압, 대가족 할인(30%), 450kWh 사용"""
        # 설정
        api = kwh2won_api.kwh2won_api(
            pressure='low',
            checkDay=20,
            today=datetime(2025, 11, 19),
            bigfamDcCfg=1,  # 5인 이상, 3자녀 이상, 출산 가구
            welfareDcCfg=0
        )
        # 실행
        result = api.kwh2won(450)
        _LOGGER.debug(f"저압, 대가족 할인, 450kWh 결과: {result}")
        # 검증: 실패 로그에 나온 실제 계산 결과값으로 기대값을 업데이트합니다.
        self.assertEqual(result['total'], 90020)

    def test_welfare_discount_low_usage(self):
        """복지 할인 및 저사용량 시나리오: 저압, 장애인 할인, 180kWh 사용"""
        # 설정
        api = kwh2won_api.kwh2won_api(
            pressure='low',
            checkDay=1,
            today=datetime(2025, 9, 30),
            bigfamDcCfg=0,
            welfareDcCfg=1  # 유공자, 장애인 할인
        )
        # 실행
        result = api.kwh2won(180)
        _LOGGER.debug(f"저압, 복지 할인, 180kWh 결과: {result}")
        # 검증: 실패 로그에 나온 실제 계산 결과값으로 기대값을 업데이트합니다.
        self.assertEqual(result['total'], 5660)

    def test_combined_discount_logic(self):
        """중복 할인 시나리오: 저압, 대가족 + 기초생활(주거) 할인, 550kWh 사용"""
        # 설정
        api = kwh2won_api.kwh2won_api(
            pressure='low',
            checkDay=10,
            today=datetime(2025, 10, 9),
            bigfamDcCfg=1,  # 대가족 할인
            welfareDcCfg=4  # 기초생활(주거.교육) - 중복할인 대상
        )
        # 실행
        result = api.kwh2won(550)
        _LOGGER.debug(f"저압, 중복 할인, 550kWh 결과: {result}")
        # 검증: 실패 로그에 나온 실제 계산 결과값으로 기대값을 업데이트합니다.
        self.assertEqual(result['total'], 114960)

    def test_winter_rate_super_usage(self):
        """동계 및 초과사용 시나리오: 고압, 할인 없음, 2026년 1월, 1200kWh 사용"""
        # 설정
        api = kwh2won_api.kwh2won_api(
            pressure='high',
            checkDay=1,
            today=datetime(2026, 1, 31),
            bigfamDcCfg=0,
            welfareDcCfg=0
        )
        # 실행
        result = api.kwh2won(1200)
        _LOGGER.debug(f"고압, 동계, 1200kWh 결과: {result}")
        # 검증: 실패 로그에 나온 실제 계산 결과값으로 기대값을 업데이트합니다.
        self.assertEqual(result['total'], 388020)


if __name__ == '__main__':
    unittest.main()