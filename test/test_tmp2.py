
import datetime

import logging
_LOGGER = logging.getLogger(__name__)


# 로그의 출력 기준 설정
_LOGGER.setLevel(logging.DEBUG)
# log 출력 형식
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# log 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
_LOGGER.addHandler(stream_handler)

NOW = datetime.datetime.now()

class test():
    
    def __init__(self):
        ret = {
            'today' : datetime.datetime(2021,12,21, 1,0,0), # 오늘
            # 'today': NOW,
            'checkDay' : 0, # 검침일
            'monthDays': 0, # 월일수
        }
        self._ret = ret
        self.calc_lengthDays()
    
    # 월별 동계, 하계 일수 구하기
    # checkDay = 시작일
    def calc_lengthUseDays(self) :
        checkDay = self._ret['checkDay']
        checkMonth = self._ret['checkMonth']
        monthDays = self._ret['monthDays']
        today = int(self._ret['today'].strftime('%d'))
        etc = 0
        winter = 0
        summer = 0
        moons = {
            checkMonth : monthDays - checkDay +1,
            checkMonth+1 : checkDay -1
        }
        for moon, moonleng in moons.items():
            if moon in [7,8] :
                summer += moonleng
            elif moon in [12,1,2] :
                winter += moonleng
            else :
                etc += moonleng
        if checkMonth in [7,8] :
            season = 'summer'
        elif checkMonth in [12,1,2] :
            season = 'winter'
        else :
            season = 'etc'

        _LOGGER.debug(f'검침월:{checkMonth}')
        _LOGGER.debug(f'검침일:{checkDay}')
        _LOGGER.debug(f"시즌일수: 기타 {etc}, 동계 {winter}, 하계 {summer}, 현시즌:{season} ")


    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)


    # 월 사용일 구하기
    def calc_lengthDays(self) :
        today = self._ret['today']
        checkDay = self._ret['checkDay']
        checkDay_tmp = checkDay
        if (checkDay == 0): # 말일미면, 말일로 셋팅
            checkDay = self.last_day_of_month(today)
            checkDay = checkDay.day
        if today.day >= checkDay : # 오늘이 검침일보다 크면
            lastday = self.last_day_of_month(today) # 달의 마지막일이 전체 길이
        else : # 오늘이 검칠일보다 작으면
            lastday = today - datetime.timedelta(days=today.day) # 전달의 마지막일이 전체 길이
        self._ret['checkMonth'] = lastday.month
        self._ret['monthDays'] = lastday.day
        if (checkDay_tmp == 0): # 말일미면, 말일로 셋팅
            self._ret['checkDay'] = lastday.day
        _LOGGER.debug(f"월일수:{lastday.day} ({lastday.month}월)")
        # _LOGGER.debug(f'월일수: {monthDays}')

    # 예상 사용량
    # 사용일 = (오늘 > 검침일) ? 오늘 - 검침일 : 전달일수 - 검침일 + 오늘
    # 월일수 = (오늘 > 검침일) ? 이번달일수 : 전달일수
    # 시간나누기 = ((사용일-1)*24)+(현재시간+1)
    # 시간곱하기 = 월일수*24
    # 예측 = 에너지 / 시간나누기 * 시간곱하기
    def energy_forecast(self, energy):
        # energy = self._ret['energy']
        today = self._ret['today']
        checkDay = self._ret['checkDay']
        if today.day >= checkDay :
            lastday = self.last_day_of_month(today)
            lastday = lastday.day
            useday = today.day - checkDay +1
        else :
            lastday = today - datetime.timedelta(days=today.day)
            lastday = lastday.day
            useday = lastday + today.day - checkDay +1
        forcest = round(energy / (((useday - 1) * 24) + today.hour + 1) * (lastday * 24), 1)
        _LOGGER.debug(f"예상사용량:{forcest}, 월길이 {lastday}, 사용일 {useday}, 검침일 {checkDay}, 오늘 {today.day}")
        return {
            'forcest': forcest,
            'lastday': lastday,
            'useday': useday,
            'checkDay': checkDay,
            'today': today.day,
        }

K2W = test()
K2W.calc_lengthUseDays()
ret = K2W.energy_forecast(200)
print(ret)