import unittest
from datetime import datetime
import kwh2won_api
import logging

class TestKwh2WonAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        _LOGGER.addHandler(stream_handler)
        cls._LOGGER = _LOGGER

        # kwh2won_api의 로그 레벨을 디버그로 설정
        kwh2won_logger = logging.getLogger('kwh2won_api')
        kwh2won_logger.setLevel(logging.DEBUG)
        kwh2won_logger.addHandler(stream_handler)

    def setUp(self):
        self.pressure = 'high'  # 'low' or 'high'
        self.checkDay = 18
        self.today = datetime(2025, 8, 17, 22, 42, 0)
        
        # A1 : 5인이상 가구,출산가구,3자녀이상 가구 (16,000원 한도)
        # A2 : 생명유지장치 (한도 없음)
        self.bigfamDcCfg = 0  # 0, 1, or 2
        
        # B1 : 독립유공자,국가유공자,5.18민주유공자,장애인 (16,000원 한도)
        # B2 : 사회복지시설 (전기요금계((기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) － 필수사용량 보장공제) x 30%, 한도 없음)
        # B3 : 기초생활(생계.의료) (16,000원 한도) + 중복할인
        # B4 : 기초생활(주거.교육) (10,000원 한도) + 중복할인
        # B5 : 차사위계층 (8,000원 한도) + 중복할인
        self.welfareDcCfg = 0  # 0 to 5
        self.kWh = 500
        self.K2W = kwh2won_api.kwh2won_api(
            pressure=self.pressure,
            checkDay=self.checkDay,
            today=self.today,
            bigfamDcCfg=self.bigfamDcCfg,
            welfareDcCfg=self.welfareDcCfg
        )

    def test_kwh2won(self):
        ret = self.K2W.kwh2won(self.kWh)
        self._LOGGER.debug(f'Result: {ret}')
        self.assertIsNotNone(ret)


if __name__ == '__main__':
    unittest.main()

# def calc_elec():
#     result = []
#     for i in range(30):
#         a = kwh2won_api.kwh2won_api(pressure = 'high', checkDay = i + 1)
#         result.append({i: {'total': a.kwh2won(500)['total'],'checkMonth': a.kwh2won(500)['checkMonth'],'checkDay': a.kwh2won(500)['checkDay']}})
#     return {'result': result}

# b = calc_elec()
# print(b)