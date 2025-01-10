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
        self.cfg = {
            'pressure': 'low',
            'checkDay': 11,
            'today': datetime(2024, 6, 24, 22, 42, 0),
            'bigfamDcCfg': 0,
            'welfareDcCfg': 0,
        }
        self.K2W = kwh2won_api.kwh2won_api(self.cfg)

    def test_kwh2won(self):
        ret = self.K2W.kwh2won(400)
        self._LOGGER.debug(f'Result: {ret}')
        self.assertIsNotNone(ret)

if __name__ == '__main__':
    unittest.main()