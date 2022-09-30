import math
import datetime
from dateutil.relativedelta import relativedelta
import logging
_LOGGER = logging.getLogger(__name__)

# # 로그의 출력 기준 설정
# _LOGGER.setLevel(logging.DEBUG)
# # log 출력 형식
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# # log 출력
# stream_handler = logging.StreamHandler()
# stream_handler.setFormatter(formatter)
# _LOGGER.addHandler(stream_handler)

import collections
from copy import deepcopy
def merge(dict1, dict2):
    ''' Return a new dictionary by merging two dictionaries recursively. '''
    result = deepcopy(dict1)
    for key, value in dict2.items():
        if isinstance(value, collections.abc.Mapping):
            result[key] = merge(result.get(key, {}), value)
        else:
            result[key] = deepcopy(dict2[key])
    return result


# https://cyber.kepco.co.kr/ckepco/front/jsp/CY/E/E/CYEEHP00101.jsp


PRICE_BASE = {
    'low': {
        'basicPrice' : [910, 1600, 7300, 7300],    # 기본요금(원/호)
        'kwhPrice' : [98.1, 192.7, 285.4, 704.5],   # 전력량 요금(원/kWh) - (환경비용차감을 반영한 단가)
        'kwhSection': {
            'etc' : [200, 400, 10000],    # 구간(kWh - 기타)
            'winter' : [200, 400, 1000, 10000],    # 구간(kWh - 동계)
            'summer' : [300, 450, 1000, 10000]   # 구간(kWh - 하계)(7~8월)
        },
        'elecBasicLimit' : 2000,     # 필수사용공제
        'elecBasic200Limit' : 4000   # 200kWh이하 감액
    },
    'high': {
        'basicPrice' : [730, 1260, 6060, 6060],  # 기본요금(원/호)
        'kwhPrice' : [83.1, 152.1, 220.4, 569.6], # 전력량 요금(원/kWh) - (환경비용차감을 반영한 단가
        'kwhSection': {
            'etc' : [200, 400, 10000],   # 구간(kWh - 기타)
            'winter' : [200, 400, 1000, 10000],   # 구간(kWh - 동계)
            'summer' : [300, 450, 1000, 10000], # 구간(kWh - 하계)(7~8월)
        },
        'elecBasicLimit' : 1500,     # 필수사용공제
        'elecBasic200Limit' : 2500   # 200kWh이하 감액
    },
    'adjustment' : [6.7, 7.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
    'dc': {
        'etc': {
            'a1': 16000, # 5인이상 가구,출산가구,3자녀이상 가구
            'a2': 0.3,   # 생명유지장치
            'b1': 16000, # 독립유공자,국가유공자,5.18민주유공자,장애인 
            'b2': 0.3,   # 사회복지시설
            'b3': 16000, # 기초생활(생계.의료)
            'b4': 10000, # 기초생활(주거.교육)
            'b5': 8000,  # 차사위계층
        },
        'summer': { # 6~8월
            'a1': 16000,
            'a2': 0.3,
            'b1': 20000,
            'b2': 0.3,
            'b3': 20000,
            'b4': 12000,
            'b5': 10000,
        }
    }
}


# 전력량 요금(원/kWh) - (환경비용차감을 반영한 단가)
PRICE_KWH = {
    '2101': {
        'low':  { 'kwhPrice' : [88.3, 182.9, 275.6, 704.5] },
        'high': { 'kwhPrice' : [73.3, 142.3, 210.6, 569.6] }
    },
    '2204': { # 4.9원 인상
        'low':  { 'kwhPrice' : [93.2, 187.8, 280.5, 709.4] },
        'high': { 'kwhPrice' : [78.2, 147.2, 215.5, 574.5] }
    },
    '2210': { # 예정 인상분 4.9원 + 추가 인상 2.5원
        'low':  { 'kwhPrice' : [100.6, 195.2, 287.9, 716.8] },
        'high': { 'kwhPrice' : [85.6, 154.6, 222.9, 581.9] }
    }
}

# 환경비용차감 + 기후환경요금 + 연료비조정액
PRICE_ADJUSTMENT = {
    '2101': { 'adjustment' : [5, 5.3, -3] },
    '2109': { 'adjustment' : [5, 5.3, 0] }, # RPS 4.5 + ETS 0.5 + 석탄발전 감축비용 0.3
    '2204': { 'adjustment' : [6.7, 7.3, 0] }, # RPS 5.9 + ETS 0.8 + 석탄발전 감축비용 0.6
    '2207': { 'adjustment' : [6.7, 7.3, 5] }, # RPS 5.9 + ETS 0.8 + 석탄발전 감축비용 0.6, 7월~9월 연료비 조정액 +5원으로 확정
    '2210': { 'adjustment' : [6.7, 7.3, 5] }, # RPS 5.9 + ETS 0.8 + 석탄발전 감축비용 0.6, 10월~12월 연료비 조정액 +5원으로 확정
}

# 필수사용량보장공제
PRICE_ELECBASIC = {
    '2101': {
        'low':  { 'elecBasicLimit' : 4000 },
        'high': { 'elecBasicLimit' : 2500 }
    },
    '2109': {
        'low':  { 'elecBasicLimit' : 2000 },
        'high': { 'elecBasicLimit' : 1500 }
    },
    '2207': {
        'low':  { 'elecBasicLimit' : 0 },
        'high': { 'elecBasicLimit' : 0 }
    },
}

# 할인
PRICE_DC = {
    '2101': {},
    '2207': {
        'dc': {
            'etc': {
                'a1': 22000, # 5인이상 가구,출산가구,3자녀이상 가구
                'a2': 0.3,   # 생명유지장치
                'b1': 23600, # 독립유공자,국가유공자,5.18민주유공자,장애인 
                'b2': 0.3,   # 사회복지시설
                'b3': 23900, # 기초생활(생계.의료)
                'b4': 15600, # 기초생활(주거.교육)
                'b5': 12600,  # 차사위계층
            },
            'summer': { # 6월 ~ 8월
                'a1': 22000,
                'a2': 0.3,
                'b1': 29600,
                'b2': 0.3,
                'b3': 29600,
                'b4': 18600,
                'b5': 15600,
            }
        }
    },
    '2210': {
        'dc': {
            'etc': {
                'a1': 22000, # 5인이상 가구,출산가구,3자녀이상 가구
                'a2': 0.3,   # 생명유지장치
                'b1': 22000, # 독립유공자,국가유공자,5.18민주유공자,장애인 
                'b2': 0.3,   # 사회복지시설
                'b3': 23900, # 기초생활(생계.의료)
                'b4': 14000, # 기초생활(주거.교육)
                'b5': 11000,  # 차사위계층
            }
        }
    },
    '2301': {}
}


class kwh2won_api:
    def __init__(self, cfg):
        ret = {
            'energy': 0.0001,     # 사용량
            'pressure' : 'low',
            'checkDay' : 0, # 검침일
            # 'today' : datetime.datetime(2022,7,10, 1,0,0), # 오늘
            'today': datetime.datetime.now(),
            'bigfamDcCfg' : 0, # 대가족 요금할인
            'welfareDcCfg' : 0, # 복지 요금할인
            'checkYear':0, # 검침년
            'checkMonth':0, # 검침월
            'monthDays': 0, # 월일수
            'useDays': 0, # 사용일수
            'mm1' : {
                'yymm': '',     # 사용년월
                'season': 'etc', # 시즌
                'energy': 0,     # 사용량
                'basicWon': 0,   # 기본요금
                'kwhWon': 0,     # 전력량요금
                'diffWon': 0,    # 환경비용차감
                'climateWon': 0, # 기후환경요금
                'useDays': 0,    # 사용일수
                'kwhStep': 0,    # 누진단계
                'welfareDc': 0,  # 복지할인
                'bigfamDc': 0,   # 대가족할인
                'elecBasicDc': 0, # 필수사용량보장공제
            },
            'mm2' : {
                'yymm': '',     # 사용년월
                'season': 'etc', # 시즌
                'energy': 0,     # 사용량
                'basicWon': 0,   # 기본요금
                'kwhWon': 0,     # 전력량요금
                'diffWon': 0,    # 환경비용차감
                'climateWon': 0, # 기후환경요금
                'useDays': 0,    # 사용일수
                'kwhStep': 0,    # 누진단계
                'welfareDc': 0,  # 복지할인
                'bigfamDc': 0,   # 대가족할인
                'elecBasicDc': 0, # 필수사용량보장공제
            },
            'basicWon': 0,   # 기본요금
            'kwhWon': 0,     # 전력량요금
            'diffWon': 0,    # 환경비용차감
            'climateWon': 0, # 기후환경요금
            'fuelWon': 0,    # 연료비조정액
            'elecBasicDc': 0, # 필수사용량보장공제
            'elecBasic200Dc': 0, # 200kWh이하 감액
            'bigfamDc': 0,   # 대가족 요금할인
            'welfareDc': 0,  # 복지 요금할인
            'elecSumWon': 0,     # 전기요금계
            'vat': 0, # 부가가치세
            'baseFund': 0, # 전력산업기반기금
            'total': 0, # 청구금액
        }
        ret.update(cfg)
        self._ret = ret



    # 당월 단가 찾기
    def price_find(self, prices, yymm):
        cnt = -1
        listym = list(prices.keys())
        for ym in listym :
            if ym <= yymm:
                cnt += 1
            else :
                break
        if cnt == -1 :
            cnt = 0
        return listym[cnt]



    # 예상 사용량
    # 사용일 = (오늘 > 검침일) ? 오늘 - 검침일 : 전달일수 - 검침일 + 오늘
    # 월일수 = (오늘 > 검침일) ? 이번달일수 : 전달일수
    # 시간나누기 = ((사용일-1)*24)+(현재시간+1)
    # 시간곱하기 = 월일수*24
    # 예측 = 에너지 / 시간나누기 * 시간곱하기
    def energy_forecast(self, energy, today=None):
        if today:
            self._ret['today'] = today
        self.calc_lengthDays() # 사용일 구하기 호출
        today = self._ret['today']
        checkMonth = self._ret['checkMonth']
        checkDay = self._ret['checkDay']
        useDays = self._ret['useDays']
        monthDays = self._ret['monthDays']

        forcest = round(energy / ((((useDays - 1) * 24) + today.hour) * 60 + today.minute + 1) * (monthDays * 24 * 60), 1)
        _LOGGER.debug(f"########### 예상사용량:{forcest}, 월길이 {monthDays}, 사용일 {useDays}, 검침일 {checkDay}, 오늘 {today.day}")
        return {
            'forcest': forcest,
            'monthDays': monthDays,
            'useDays': useDays,
            'checkMonth': checkMonth,
            'checkDay': checkDay,
            'today': today.day,
        }



    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)



    # 전달 검침말일 구하기
    def prev_checkday(self, today):
        self._ret['today'] = today
        self.calc_lengthDays()
        d = datetime.date(self._ret['checkYear'], self._ret['checkMonth'], self._ret['checkDay'])
        return d - datetime.timedelta(days=1)



    # 월 사용일 구하기
    def calc_lengthDays(self) :
        today = self._ret['today']
        checkDay = self._ret['checkDay']
        if (checkDay == 0 or checkDay >= 28): # 검침일이 말일미면
            lastday = self.last_day_of_month(today) # 이번달 말일
            if today.day == lastday.day : # 오늘이 말일미면, 시작일
                next_lastday = self.last_day_of_month(today + datetime.timedelta(days=1)) # 다음달 말일
                checkYear = today.year
                checkMonth = today.month
                monthDays = next_lastday.day
                useDays = 1
                checkDay = today.day
            else : # 말일이 아니면
                prev_lastday = today - datetime.timedelta(days=today.day) # 전달 말일
                checkYear = prev_lastday.year
                checkMonth = prev_lastday.month
                monthDays = lastday.day
                useDays = today.day + 1
                checkDay = prev_lastday.day
        else :
            if today.day >= checkDay : # 오늘이 검침일보다 크면
                lastday = self.last_day_of_month(today) # 달의 마지막일이 전체 길이
                useDays = today.day - checkDay +1
            else : # 오늘이 검칠일보다 작으면
                lastday = today - datetime.timedelta(days=today.day) # 전달의 마지막일이 전체 길이
                useDays = lastday.day + today.day - checkDay +1
            checkYear = lastday.year
            checkMonth = lastday.month
            monthDays = lastday.day
        self._ret['checkYear'] = checkYear
        self._ret['checkMonth'] = checkMonth
        self._ret['monthDays'] = monthDays
        self._ret['useDays'] = useDays
        if (checkDay >= 28): # 말일미면, 말일로 다시 셋팅
            self._ret['checkDay'] = checkDay
        _LOGGER.debug(f"## 검침시작 {checkYear}년 {checkMonth}월 {self._ret['checkDay']}일, 오늘 {today.month}월 {today.day}일, 검침일수:{monthDays}, 사용일수{useDays}, 남은일수{monthDays - useDays}")



    # 월별 동계, 하계 일수 구하기
    # checkDay = 시작일
    def calc_lengthUseDays(self) :
        checkDay = self._ret['checkDay']
        checkYear = self._ret['checkYear']
        checkMonth = self._ret['checkMonth']
        monthDays = self._ret['monthDays']
        etc = 0
        winter = 0
        summer = 0

        if checkMonth == 12 :
            nextYear = checkYear + 1
            nextMonth = 1
        else :
            nextYear = checkYear
            nextMonth = checkMonth + 1
        months = [
            ("mm1", checkYear, checkMonth , monthDays - checkDay +1),
            ("mm2", nextYear, nextMonth , checkDay -1)
        ]
        
        mmdiff = []
        # 전력량요금 계산에 사용
        for mm, year, month, monthleng in months:
            if month in [7,8] :
                summer += monthleng
                season = 'summer'
            elif month in [12,1,2] :
                winter += monthleng
                season = 'winter'
            else :
                etc += monthleng
                season = 'etc'
            yymm = ((year-2000)*100) + month
            yymm = f'{yymm}'
            self._ret[mm]['yymm'] = yymm
            self._ret[mm]['season'] = season
            self._ret[mm]['useDays'] = monthleng

            adjustYymm = self.price_find(PRICE_ADJUSTMENT, yymm)
            kwhYymm = self.price_find(PRICE_KWH, yymm)
            elecbacictYymm = self.price_find(PRICE_ELECBASIC, yymm)
            dcYymm = self.price_find(PRICE_DC, yymm)
            _LOGGER.debug(f'{mm} : season{season} + adjust{adjustYymm} + kwh{kwhYymm} + elecbacict{elecbacictYymm} + dc{dcYymm}')
            mmdiff.append(season + adjustYymm + kwhYymm + elecbacictYymm + dcYymm)

        # 시즌이 같고, 단가가 같으면 사용일을 하나로 합치기
        if mmdiff[0] == mmdiff[1] :
            self._ret['mm1']['useDays'] += self._ret['mm2']['useDays']
            self._ret['mm2']['useDays'] = 0

        _LOGGER.debug(f'검침월:{checkMonth} , 검침일:{checkDay}')
        _LOGGER.debug(f"시즌일수: 기타 {etc}, 동계 {winter}, 하계 {summer}, 현시즌:{season} ")



    # 전기요금 계산(주거용) 
    # 기본요금(원 미만 절사)
    # 전력량요금(원 미만 절사) 
    # 환경비용차감(원 미만 절사)
    # 기후환경요금(원 미만 절사)
    #  예시에 따라 아래와 같이 계산됩니다(기본요금·연료비조정요금 미반영). 
    # ==================================================== 
    #  (예시) 사용기간 `22. 3. 11 ~ `22. 4. 10, 검침일 11일, 사용량 350kWh 
    #   * ’22.4.1일부로 현행 전력량요금에서 +4.9원/㎾h 인상 적용 
    # ==================================================== 
    #   가. 전력량요금 : 45,648원(원 미만 절사) 
    #    ○ (1단계) 200kWh×88.3원×(21/31)일 + 200kWh×93.2원×(10/31)일 = 17,976원 
    #    ○ (2단계) 150kWh×182.9원×(21/31)일 + 150kWh×187.8원×(10/31)일 = 27,672원 
    #   나. 기후환경요금 : 2,080원(원 미만 절사) 
    #    ○ 350kWh×5.3×(21/31)일 + 350kWh×7.3×(10/31)일 = 2,080원 
    #   ☞  전기요금 = 47,728원(45,648원 + 2,080원)  
    def calc_prog(self):

        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        basicPrice = PRICE_BASE[pressure]['basicPrice'] # 기본요금(원/호)
        monthDays = self._ret['monthDays'] # 월일수
        basicWonSum = 0
        kwhWonSum = 0
        diffWonSum = 0 # 환경비용차감
        climateWonSum = 0 # 기후환경요금(원미만 절사)

        _LOGGER.debug(f"누진요금구하기 ===== ")
        # 시즌 요금 구하기
        for mm in ['mm1','mm2'] :
            seasonDays = self._ret[mm]['useDays'] # 사용일수
            if (seasonDays == 0) :
                continue
            yymm = self._ret[mm]['yymm'] # 사용연월
            priceYymm = self.price_find(PRICE_ADJUSTMENT, yymm)
            calcPrice = merge(PRICE_BASE, PRICE_ADJUSTMENT[priceYymm])
            priceYymm = self.price_find(PRICE_KWH, yymm)
            calcPrice = merge(calcPrice, PRICE_KWH[priceYymm])
            diffPrice = calcPrice['adjustment'][0] # 환경비용차감 단가
            climatePrice = calcPrice['adjustment'][1] # 기후환경요금 단가
            kwhPrice = calcPrice[pressure]['kwhPrice'] # 전력량 단가(원/kWh)
            season = self._ret[mm]['season'] # 사용연월
            kwhSection = calcPrice[pressure]['kwhSection'][season] # 누진구간(kWh)
            kwhStep = 0 # 누진단계
            basicWon = 0 # 기본요금
            kwhWon = 0 # 전력량요금
            diffWon = 0 # 환경비용차감
            seasonEnergy = energy * seasonDays / monthDays
            _LOGGER.debug(f"  사용월:{yymm}, 사용일:{seasonDays}, 에너지: {round(seasonEnergy)}, 시즌: {season} (단가월: {priceYymm}) ")
            restEnergy = energy # 계산하고 남은 
            kwhWonSeason = 0 # 시즌전력량요금
            stepEnergyCalcSum = 0 # 구간 사용량 합계
            for stepkwh in kwhSection:
                if (restEnergy <= 0) : 
                    break
                elif (energy > stepkwh) : # 다음 구간이 남아 있으면
                    stepEnergy = stepkwh - (energy - restEnergy) # 계산될 현단계 energy
                    restEnergy = energy - stepkwh # # 계산하고 남은 
                    stepEnergyCalc = round(stepEnergy / monthDays * seasonDays) # 구간 사용량 계산
                else : # 마지막 구간
                    stepEnergy = restEnergy
                    restEnergy = 0
                    stepEnergyCalc = round(energy / monthDays * seasonDays) - stepEnergyCalcSum # 구간 사용량 계산
                kwhStep += 1 # 누진 단계
                stepEnergyCalcSum += stepEnergyCalc
                kwhWon = round(stepEnergyCalc * (kwhPrice[kwhStep-1] + diffPrice), 2) # 구간 요금 계산
                kwhWonSeason += kwhWon
                kwhWonSum += kwhWon
                _LOGGER.debug(f"    {kwhStep}단계, 구간에너지 : {stepEnergy} (~{stepkwh}), 구간전력량요금 : {kwhWon}원 = ({stepEnergy}kWh * {seasonDays}d / {monthDays}d):{stepEnergyCalc}kWh * {kwhPrice[kwhStep-1]}원") # 구간 요금 계산
            basicWon = basicPrice[kwhStep-1] * seasonDays / monthDays
            basicWonSum += basicWon
            diffWon = round((energy * diffPrice) * seasonDays / monthDays , 2) # 환경비용차감
            diffWonSum += diffWon # 환경비용차감
            climateWon = round((energy * climatePrice) * seasonDays / monthDays , 2) # 기후환경요금
            climateWonSum += climateWon # 기후환경요금
            self._ret[mm]['basicWon'] = round(basicWon)
            self._ret[mm]['kwhWon'] = kwhWonSeason
            self._ret[mm]['kwhStep'] = kwhStep
            self._ret[mm]['diffWon'] = diffWon
            self._ret[mm]['climateWon'] = climateWon
            _LOGGER.debug(f"    시즌요금{round(basicWon)+round(kwhWonSeason)-diffWon+climateWon} = 시즌기본요금:{round(basicWon)}원, 시즌전력량요금:{round(kwhWonSeason)}원, 환경비용차감:-{diffWon}, 기후환경요금:{climateWon}")
        basicWonSum = math.floor(basicWonSum) # 기본요금합
        kwhWon = math.floor(kwhWonSum - diffWonSum) # 전력량요금 (원 미만 절사) 
        self._ret['kwhWon'] = kwhWon # 전력량요금(원 미만 절사) 
        self._ret['basicWon'] = math.floor(basicWonSum) # 기본요금(원 미만 절사)
        self._ret['diffWon'] = math.floor(diffWonSum) # 환경비용차감(원 미만 절사)
        self._ret['climateWon'] = math.floor(climateWonSum) # 기후환경요금(원 미만 절사)
        _LOGGER.debug(f"  기본요금합:{basicWonSum}원, 전력량요금합:{math.floor(kwhWonSum)}원, 환경비용차감:{round(diffWonSum)}원")
        _LOGGER.debug(f"  전력량요금:{kwhWon}원 = 전력량요금합:{math.floor(kwhWonSum)} - 환경비용차감:{round(diffWonSum)}")
        _LOGGER.debug(f"  기후환경요금:{math.floor(climateWonSum)}원")



    # 연료비조정액(원미만 절사) : -1,500원
    # 500kWh × -3원 = -1,500원
    # * 연료비조정액은 일수계산 안 함
    # 요금 산정기준은 검침일인데 6월1일부터6월30일 까지 사용한것을 7월1일 검침하는 것 
    def calc_fuelWon(self) :
        # 검침 시작일의 한달 후를 구함.
        d = datetime.date(self._ret['checkYear'], self._ret['checkMonth'], self._ret['checkDay'])
        d = d + relativedelta(months=1)
        yymm = d.strftime("%y%m")
        
        priceYymm = self.price_find(PRICE_ADJUSTMENT, yymm)
        calcPrice = merge(PRICE_BASE, PRICE_ADJUSTMENT[priceYymm])
        energy = self._ret['energy'] # 사용전력
        fuelPrice = calcPrice['adjustment'][2] # 연료비조정액 단가
        fuelWon = math.floor(energy * fuelPrice)
        _LOGGER.debug(f"  연료비조정액:{fuelWon}원 = 사용량:{energy}kWh * 연료비조정단가:{fuelPrice}원")
        self._ret['fuelWon'] = fuelWon



    # 필수사용량 보장공제(원미만 절사)
    # 가정용 저압 [200kWh 이하, 최대 2,000원]
    # 가정용 고압, 복지할인시 [200kWh 이하, 2,500원]
    # (기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) - 1000
    # 일할
    def calc_elecBasic(self) :
        for mm in ['mm1','mm2'] :
            seasonDays = self._ret[mm]['useDays'] # 사용일수
            if (seasonDays == 0) :
                continue
            priceYymm = self.price_find(PRICE_ELECBASIC, self._ret[mm]['yymm'])
            calcPrice = merge(PRICE_BASE, PRICE_ELECBASIC[priceYymm])
            monthDays = self._ret['monthDays'] # 월일수
            energy = self._ret['energy'] # 사용전력
            pressure = self._ret['pressure'] # 계약전력
            elecBasicLimit = calcPrice[pressure]['elecBasicLimit'] # 최대할인액
            elecBasic = 200
            if (elecBasicLimit > 0 and energy <= elecBasic) :
                elecBasicDc = math.floor(self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['diffWon'] + self._ret['fuelWon'] - 1000)
                if elecBasicDc > elecBasicLimit :
                    elecBasicDc = elecBasicLimit
                elecBasicDc = math.floor(elecBasicDc * seasonDays / monthDays * 100) / 100
                _LOGGER.debug(f"필수사용량 보장공제:{elecBasicDc} = {elecBasicLimit} or (기본요금합:{self._ret['basicWon']}원, 전력량요금합:{self._ret['kwhWon']}원, 환경비용차감:{self._ret['diffWon']}원 - 1000) * {seasonDays} / {monthDays}") 
                self._ret[mm]['elecBasicDc'] = elecBasicDc
        self._ret['elecBasicDc'] = math.floor(self._ret['mm1']['elecBasicDc'] + self._ret['mm2']['elecBasicDc'])


    # 200kWh 이하 감액(원미만 절사) = 저압 4,000  고압 2,500
    # 복지할인 해당시
    def calc_elecBasic200(self) :
        priceYymm = self.price_find(PRICE_ELECBASIC, self._ret['mm1']['yymm'])
        calcPrice = merge(PRICE_BASE, PRICE_ELECBASIC[priceYymm])
        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        elecBasic200Limit = calcPrice[pressure]['elecBasic200Limit'] # 최대할인액
        elecBasic = 200
        if (energy <= elecBasic) :
            self._ret['elecBasicDc'] = 0
            elecBasic200Dc = math.floor(self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['climateWon'] + self._ret['fuelWon'])
            if elecBasic200Dc > elecBasic200Limit :
                elecBasic200Dc = elecBasic200Limit
            self._ret['elecBasic200Dc'] = elecBasic200Dc
            _LOGGER.debug(f"200kWh 이하 감액:{elecBasic200Dc} = {elecBasic200Limit} or 기본요금합:{self._ret['basicWon']}원 + 전력량요금합:{self._ret['kwhWon']}원 + 기후환경요금{self._ret['climateWon']} + 연료비조정액:{self._ret['fuelWon']}원")



    # 복지 할인은 6~8월 하계 적용
    # 복지할인(독립유공자)(원미만 절사) : 16,000원
    # 독립유공자 할인 : 16,000원
    # 복지 요금할인
    # B1 : 독립유공자,국가유공자,5.18민주유공자,장애인 (16,000원 한도)
    # B2 : 사회복지시설 (전기요금계((기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) － 필수사용량 보장공제) x 30%, 한도 없음)
    # B3 : 기초생활(생계.의료) (16,000원 한도) + 중복할인
    # B4 : 기초생활(주거.교육) (10,000원 한도) + 중복할인
    # B5 : 차사위계층 (8,000원 한도) + 중복할인
    # B  : 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인)
    # B2 :              전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인 － 필수사용량 보장공제)
    def calc_welfareDc(self) :
        _LOGGER.debug(f"복지할인 구하기 =====")
        monthDays = self._ret['monthDays'] # 월일수
        welfareDcCfg = self._ret['welfareDcCfg'] # 할인 종류
        for mm in ['mm1','mm2'] :
            welfareDc = math.floor(self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['climateWon'] + self._ret['fuelWon'])
            seasonDays = self._ret[mm]['useDays'] # 사용일수
            if (seasonDays == 0) :
                continue
            yymm = self._ret[mm]['yymm'] # 사용연월
            priceYymm = self.price_find(PRICE_DC, yymm)
            calcPrice = merge(PRICE_BASE, PRICE_DC[priceYymm])
            if yymm[-2:] in ['06', '07', '08'] :
                season = 'summer'
            else :
                season = 'etc'
            dc = calcPrice['dc'][season] # 할인액
            _LOGGER.debug(f"  사용월:{yymm}, 사용일:{seasonDays}/{monthDays}, 시즌:{season}, 단가월:{priceYymm}, 전기요금계:{welfareDc} ")
            # pprint.pprint(dc)
            if (welfareDcCfg == 1) : # B1
                if (welfareDc > dc['b1']) :
                    welfareDc = dc['b1']
                _LOGGER.debug(f"    유공자,장애인할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b1']}")
            elif (welfareDcCfg == 2) :
                welfareDc = welfareDc * dc['b2']
                _LOGGER.debug(f"    사회복지시설할인 : {welfareDc} = (전기요금계 - 필수사용량 보장공제 ) x {dc['b2']}, 한도 없음")
            elif (welfareDcCfg == 3) :
                if (welfareDc > dc['b3']) :
                    welfareDc = dc['b3']
                _LOGGER.debug(f"    기초생활(생계.의료)할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b3']}")
            elif (welfareDcCfg == 4) :
                if (welfareDc > dc['b4']) :
                    welfareDc = dc['b4']
                _LOGGER.debug(f"    기초생활(주거.교육)할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b4']}")
            elif (welfareDcCfg == 5) :
                _LOGGER.debug(f"    {welfareDc} , {dc['b5']}")
                if (welfareDc > dc['b5']) :
                    welfareDc = dc['b5']
                _LOGGER.debug(f"    차사위계층할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b5']}")
            self._ret[mm]['welfareDc'] = round( welfareDc / monthDays * seasonDays * 100 ) / 100
            _LOGGER.debug(f"    일할계산 {self._ret[mm]['welfareDc']} = {welfareDc} / {monthDays} * {seasonDays}")
        self._ret['welfareDc'] = math.floor( self._ret['mm1']['welfareDc'] + self._ret['mm2']['welfareDc'] )
        _LOGGER.debug(f"  복지할인 = {self._ret['welfareDc']}")


    # 복지 할인은 6~8월 하계 적용
    # 대가족 요금(원미만 절사) : 16,000원
    # 대가족 요금 : 16,000원
    # - 대가족 요금 : 16,000원
    # 6월 계산분 : (2,433.3원 + 27,265.2원 + 885.1원 － 501원) × 30% = 9,024.8원, 5,333.3원 한도
    # 7월 계산분 : (4,866.7원 + 45,044.8원 + 1,764.9원 － 999원) × 30% = 15,203.2원, 10,666.7원 한도
    # 대가족 요금할인
    # A1 : 5인이상 가구,출산가구,3자녀이상 가구 (16,000원 한도)
    # A2 : 생명유지장치 (한도 없음)
    # 전기요금계((기본요금 ＋ 전력량요금 － 필수사용량 보장공제 ＋ 기후환경요금 ± 연료비조정액) － 200kWh이하감액) x 30% = 대가족 요금할인
    def calc_bigfamDc(self) :
        _LOGGER.debug(f"대가족요금할인 구하기 =====")
        monthDays = self._ret['monthDays'] # 월일수
        bigfamDcCfg = self._ret['bigfamDcCfg']
        welfareDcCfg = self._ret['welfareDcCfg'] # 할인 종류
        elecBasic200Dc = self._ret['elecBasic200Dc']
        welfareDc = self._ret['welfareDc']
        for mm in ['mm1','mm2'] :
            seasonDays = self._ret[mm]['useDays'] # 사용일수
            if (seasonDays == 0) :
                continue
            yymm = self._ret[mm]['yymm'] # 사용연월
            priceYymm = self.price_find(PRICE_DC, yymm)
            calcPrice = merge(PRICE_BASE, PRICE_DC[priceYymm])
            if yymm[-2:] in ['06', '07', '08'] :
                season = 'summer'
            else :
                season = 'etc'
            dc = calcPrice['dc'][season] # 최대할인액
            _LOGGER.debug(f"  사용월:{yymm}, 사용일:{seasonDays}/{monthDays}, 시즌:{season}, 단가월:{priceYymm} ")

            welfareDc_temp = 0
            if (welfareDcCfg >= 2) : # A2
                welfareDc_temp = self._ret[mm]['welfareDc']
            fuelWon = math.floor(self._ret['fuelWon'] * self._ret[mm]['useDays'] / self._ret['monthDays'])
            kwhWonDcLimit = math.floor(self._ret[mm]['basicWon']) + math.floor(self._ret[mm]['kwhWon']) - math.floor(self._ret[mm]['diffWon']) + math.floor(self._ret[mm]['climateWon']) + fuelWon
            bigfamDc2 = round(dc['a1'] / monthDays * seasonDays *100)/100
            bigfamDc1 = round((kwhWonDcLimit - elecBasic200Dc - welfareDc_temp) * 0.3)
            _LOGGER.debug(f"    할인액30%:{bigfamDc1} = (시즌전기요금:{kwhWonDcLimit} - 200kwh이하공제:{elecBasic200Dc} - 복지할인:{welfareDc_temp}) * 30% ")

            if (bigfamDcCfg == 1) : # A1
                _LOGGER.debug(f"    할인한도:{bigfamDc2} = 할인액:{dc['a1']} / 월일수:{monthDays} * 사용일수:{seasonDays} ")
                if (bigfamDc1 > bigfamDc2) :
                    bigfamDc1 = bigfamDc2
    
            _LOGGER.debug(f"    할인금액:{bigfamDc1} ")
            self._ret[mm]['bigfamDc'] = bigfamDc1
        self._ret['bigfamDc'] = math.floor( self._ret['mm1']['bigfamDc'] + self._ret['mm2']['bigfamDc'])
        _LOGGER.debug(f"  대가족요금할인 = {self._ret['bigfamDc']}")



    # 복지할인 중복계산
    # A B 중 큰 금액 적용
    # 차사위계층,기초생활은 중복할인 (A + B)
    def calc_dc(self):
        welfareDcCfg = self._ret['welfareDcCfg']
        bigfamDc = self._ret['bigfamDc']
        welfareDc = self._ret['welfareDc']
        if (welfareDcCfg >= 3) : # 중복할인
            dcValue = math.floor( bigfamDc + welfareDc )
            _LOGGER.debug(f'복지할인 {dcValue} = 대가족 요금할인 {bigfamDc} + 복지 요금할인 {welfareDc} 중복할인')
        else :
            if (bigfamDc > welfareDc) :
                self._ret['welfareDc'] = 0
                dcValue = bigfamDc
            else :
                self._ret['bigfamDc'] = 0
                dcValue = welfareDc
            _LOGGER.debug(f'복지할인 {dcValue} = 대가족 요금할인 {bigfamDc} or 복지 요금할인 {welfareDc} 더큰것')



    # 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액)
    # :7,300원 ＋ 72,310원 ＋ 2,650원 － 1,500원 ＝ 80,760원
    # 부가가치세(원미만 4사 5입) : 80,760원 × 0.1 ＝ 8,076원
    # 전력산업기반기금(10원미만 절사) : 80,760원 × 0.037 ＝ 2,980원
    # 청구금액(전기요금계 ＋ 부가가치세 ＋ 전력산업기반기금)
    # : 80,760원 ＋ 8,076원 ＋ 2,980원 ＝ 91,810원(10원미만 절사)
    def calc_total(self) :
        basicWon = self._ret['basicWon']   # 기본요금
        kwhWon = self._ret['kwhWon']     # 전력량요금
        # diffWon = self._ret['diffWon']    # 환경비용차감
        climateWon = self._ret['climateWon'] # 기후환경요금
        fuelWon = self._ret['fuelWon']    # 연료비조정액
        elecBasicDc = self._ret['elecBasicDc'] # 필수사용량보장공제
        elecBasic200Dc = self._ret['elecBasic200Dc'] # 200kWh이하 감액
        bigfamDc = self._ret['bigfamDc']   # 대가족 요금할인
        welfareDc = self._ret['welfareDc']  # 복지 요금할인
        # 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액)
        elecSumWon = basicWon + kwhWon - elecBasicDc + climateWon + fuelWon - elecBasic200Dc - bigfamDc - welfareDc # 전기요금계
        vat = round(elecSumWon * 0.1) # 부가가치세
        baseFund = math.floor(elecSumWon * 0.037 /10)*10 # 전력산업기금
        total = math.floor((elecSumWon + vat + baseFund) /10)*10 # 청구금액
        
        if (total < 0) :
            total = 0
        # elif (energy == 0) : # 사용량이 0 이면 50% 할인
        #     total = int(total/2)

        self._ret['elecSumWon'] = elecSumWon
        self._ret['vat'] = vat # 부가가치세
        self._ret['baseFund'] = baseFund # 전력산업기반기금
        self._ret['total'] = total # 청구금액
        _LOGGER.debug(f"전기요금계{elecSumWon} = 기본요금{basicWon} + 전력량요금{kwhWon} - 필수사용량 보장공제{elecBasicDc} + 기후환경요금{climateWon} + 연료비조정액{fuelWon} - 200kWh이하 감액{elecBasic200Dc} - 대가족할인{bigfamDc} - 복지할인{welfareDc}")
        _LOGGER.debug(f"부가가치세(반올림):{vat}원 = 전기요금계{elecSumWon} * 0.1")
        _LOGGER.debug(f"전력산업기반기금(10원미만절사):{baseFund}원 = 전기요금계{elecSumWon} * 0.037")
        _LOGGER.debug(f"청구금액(10원미만절사):{total}원 = (전기요금계{elecSumWon} + 부가가치세{vat} + 전력산업기반기금{baseFund})")



    def kwh2won(self, energy, today=None) :
        
        _LOGGER.debug(f'########### 전기사용량 : {energy}')
        energy = float(energy)
        if energy == 0 :
            self._ret['energy'] = 0.0001
        else :
            self._ret['energy'] = energy

        if today:
            self._ret['today'] = today

        _LOGGER.debug(f"오늘: {self._ret['today']}, 검침일: {self._ret['checkDay']}")
        
        self.calc_lengthDays()    # 월길이
        self.calc_lengthUseDays() # 동계, 하계, 기타 기간
        self.calc_prog()          # 기본요금, 전력량요금, 기후 환경요금
        self.calc_fuelWon()       # 연료비조정액

        if (self._ret['bigfamDcCfg'] or self._ret['welfareDcCfg']) :
            self.calc_elecBasic200() # 200kWh 이하 감액
            if self._ret['welfareDcCfg']:
                self.calc_welfareDc() # 복지할인
            if self._ret['bigfamDcCfg']:
                self.calc_bigfamDc()  # 대가족할인
            self.calc_dc() # 중복할인 혹은 큰거
        else : 
            self.calc_elecBasic()    # 필수사용량 보장공제
            

        self.calc_total()         # 청구금액
        return self._ret



# cfg = {
#     'pressure' : 'low',
#     'checkDay' : 11, # 검침일
#     'today' : datetime.datetime(2022,9,10, 22,42,0), # 오늘
#     # 'today': datetime.datetime.now(),
#     'bigfamDcCfg' : 1, # 대가족 요금할인 1: 5인이상가구.출산가구.3자녀이상, 2: 생명유지장치
#     'welfareDcCfg' : 0, # 복지 요금할인 1: 유공자 장애인, 2: 사회복지시설, 3: 기초생활(생계.의료), 4: 기초생활(주거,복지), 5: 차상위계층
# }

# K2W = kwh2won_api(cfg)
# ret = K2W.kwh2won(400)
# # K2W.calc_lengthDays()
# # forc = K2W.energy_forecast(17)
# # # import pprint
# # # pprint.pprint(ret)
