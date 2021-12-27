import math
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

CALC_PARAMETER = {
    'low': {
        'basicPrice' : [910, 1600, 7300, 7300],    # 기본요금(원/호)
        'kwhPrice' : [93.3, 187.9, 280.6, 709.5],   # 전력량 요금(원/kWh) - (환경비용차감을 반영하지 않은 단가)
        'kwhSection': {
            'etc' : [200, 400, 10000],    # 구간(kWh - 기타)
            'winter' : [200, 400, 1000, 10000],    # 구간(kWh - 동계)
            'summer' : [300, 450, 1000, 10000]   # 구간(kWh - 하계)(7~8월)
        },
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액(21년8월 까지는 -3원)
        'elecBasicLimit' : 2000,     # 필수사용공제
        'elecBasic200Limit' : 4000   # 200kWh이하 감액
    },
    'high': {
        'basicPrice' : [730, 1260, 6060, 6060],  # 기본요금(원/호)
        'kwhPrice' : [78.3, 147.3, 215.6, 574.6], # 전력량 요금(원/kWh) - (환경비용차감을 반영하지 않은 단가)
        'kwhSection': {
            'etc' : [200, 400, 10000],   # 구간(kWh - 기타)
            'winter' : [200, 400, 1000, 10000],   # 구간(kWh - 동계)
            'summer' : [300, 450, 1000, 10000], # 구간(kWh - 하계)(7~8월)
        },
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 1500,     # 필수사용공제
        'elecBasic200Limit' : 2500   # 200kWh이하 감액
    },
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
        'summer': {
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
            'checkMonth':0, # 검침월
            'monthDays': 0, # 월일수
            'useDays': 0, # 사용일수
            'season': 'winter',
            'etc' : {
                'energy': 0,     # 사용량
                'basicWon': 0,   # 기본요금
                'kwhWon': 0,     # 전력량요금
                'diffWon': 0,    # 환경비용차감
                'useDays': 0,    # 사용일수
                'kwhStep': 0,    # 누진단계
            },
            'winter' : {
                'energy': 0,     # 사용량
                'basicWon': 0,   # 기본요금
                'kwhWon': 0,     # 전력량요금
                'diffWon': 0,    # 환경비용차감
                'useDays': 0,    # 사용일수
                'kwhStep': 0,    # 누진단계
            },
            'summer' : {
                'energy': 0,     # 사용량
                'basicWon': 0,   # 기본요금
                'kwhWon': 0,     # 전력량요금
                'diffWon': 0,    # 환경비용차감
                'useDays': 0,    # 사용일수
                'kwhStep': 0,    # 누진단계
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

    # 예상 사용량
    # 사용일 = (오늘 > 검침일) ? 오늘 - 검침일 : 전달일수 - 검침일 + 오늘
    # 월일수 = (오늘 > 검침일) ? 이번달일수 : 전달일수
    # 시간나누기 = ((사용일-1)*24)+(현재시간+1)
    # 시간곱하기 = 월일수*24
    # 예측 = 에너지 / 시간나누기 * 시간곱하기
    def energy_forecast(self, energy):
        self.calc_lengthDays() # 사용일 구하기 호출
        today = self._ret['today']
        checkDay = self._ret['checkDay']
        useDays = self._ret['useDays']
        monthDays = self._ret['monthDays']

        forcest = round(energy / (((useDays - 1) * 24) + today.hour + 1) * (monthDays * 24), 1)
        _LOGGER.debug(f"########### 예상사용량:{forcest}, 월길이 {monthDays}, 사용일 {useDays}, 검침일 {checkDay}, 오늘 {today.day}")
        return {
            'forcest': forcest,
            'monthDays': monthDays,
            'useDays': useDays,
            'checkDay': checkDay,
            'today': today.day,
        }

    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)


    # 월 사용일 구하기
    def calc_lengthDays(self) :
        today = self._ret['today']
        checkDay = self._ret['checkDay']
        if (checkDay == 0 or checkDay >= 28): # 말일미면, 말일로 다시 셋팅
            checkDay = self.last_day_of_month(today)
            checkDay = checkDay.day
        if today.day >= checkDay : # 오늘이 검침일보다 크면
            lastday = self.last_day_of_month(today) # 달의 마지막일이 전체 길이
            useDays = today.day - checkDay +1
        else : # 오늘이 검칠일보다 작으면
            lastday = today - datetime.timedelta(days=today.day) # 전달의 마지막일이 전체 길이
            useDays = lastday.day + today.day - checkDay +1
        self._ret['checkMonth'] = lastday.month
        self._ret['monthDays'] = lastday.day
        self._ret['useDays'] = useDays
        if (checkDay >= 28): # 말일미면, 말일로 다시 셋팅
            self._ret['checkDay'] = lastday.day
        _LOGGER.debug(f"## 월일수:{lastday.day}, ({lastday.month}월), 사용일{useDays} 검침일{self._ret['checkDay']}")
        # _LOGGER.debug(f'월일수: {monthDays}')


    # 월별 동계, 하계 일수 구하기
    # checkDay = 시작일
    def calc_lengthUseDays(self) :
        checkDay = self._ret['checkDay']
        checkMonth = self._ret['checkMonth']
        monthDays = self._ret['monthDays']
        # today = int(self._ret['today'].strftime('%m%d'))
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

        self._ret['season'] = season
        self._ret['etc']['useDays'] = etc
        self._ret['winter']['useDays'] = winter
        self._ret['summer']['useDays'] = summer

        _LOGGER.debug(f'검침월:{checkMonth} , 검침일:{checkDay}')
        _LOGGER.debug(f"시즌일수: 기타 {etc}, 동계 {winter}, 하계 {summer}, 현시즌:{season} ")


    # 전기요금 계산(주거용)
    # 기본요금
    # 전력량요금
    # 환경비용차감
    def calc_prog(self):

        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        basicPrice = CALC_PARAMETER[pressure]['basicPrice'] # 기본요금(원/호)
        kwhPrice = CALC_PARAMETER[pressure]['kwhPrice'] # 전력량 단가(원/kWh)
        diffPrice = CALC_PARAMETER[pressure]['adjustment'][0] # 환경비용차감 단가
        monthDays = self._ret['monthDays'] # 월일수
        basicWonSum = 0
        kwhWonSum = 0

        _LOGGER.debug(f"누진요금구하기 ===== ")
        # 시즌 요금 구하기
        for season in ['etc','winter','summer'] :
            seasonDays = self._ret[season]['useDays'] # 사용일수
            if (seasonDays == 0) :
                continue
            kwhSection = CALC_PARAMETER[pressure]['kwhSection'][season] # 구간 단가(kWh)
            kwhStep = 0 # 누진구간
            basicWon = 0 # 기본요금(원미만절사)
            kwhWon = 0 # 전력량요금(원미만절사)
            diffWon = 0 # 환경비용차감(원미만적사)
            seasonEnergy = energy * seasonDays / monthDays
            _LOGGER.debug(f"  시즌:{season}, 사용일:{seasonDays}, 에너지: {round(seasonEnergy)} ")
            kwhStepSum = 0
            restEnergy = energy
            for stepkwh in kwhSection:
                if (restEnergy <= 0) : 
                    break
                elif (energy > stepkwh) :
                    stepEnergy = stepkwh - kwhStepSum
                    restEnergy = energy - stepkwh
                else :
                    stepEnergy = restEnergy
                    restEnergy = 0
                kwhStep += 1 # 누진 단계
                kwhStepSum += stepEnergy
                kwhWon = round(round(stepEnergy * seasonDays / monthDays) * kwhPrice[kwhStep-1],1) # 구간 요금 계산
                kwhWonSum += kwhWon
                _LOGGER.debug(f"    {kwhStep}단계, 구간에너지 : {stepEnergy} (~{stepkwh}), 구간전력량요금 : {kwhWon}원 = ({stepEnergy}kWh * {seasonDays}d / {monthDays}d):{round(stepEnergy*seasonDays/monthDays)}kWh * {kwhPrice[kwhStep-1]}원") # 구간 요금 계산
            basicWon = math.floor(basicPrice[kwhStep-1] * seasonDays / monthDays)
            basicWonSum += basicWon
            self._ret[season]['basicWon'] = basicWon
            self._ret[season]['kwhWon'] = kwhWonSum
            self._ret[season]['kwhStep'] = kwhStep
            _LOGGER.debug(f"    시즌기본요금:{math.floor(basicWon)}원, 시즌전력량요금:{kwhWonSum}원")
        basicWonSum = math.floor(basicWonSum) # 기본요금합
        diffWon = energy * diffPrice # 환경비용차감
        kwhWon = math.floor(kwhWonSum + diffWon) # 전력량요금
        self._ret['kwhWon'] = kwhWon
        self._ret['basicWon'] = basicWonSum
        self._ret['diffWon'] = diffWon
        _LOGGER.debug(f"  기본요금합:{basicWonSum}원, 전력량요금합:{math.floor(kwhWonSum)}원, 환경비용차감:{diffWon}원 = 사용량:{energy}kWh * 환경비요차감단가:{diffPrice}원")
        _LOGGER.debug(f"  전력량요금:{kwhWon}원 = 전력량요금합:{math.floor(kwhWonSum)} + 환경비용차감:{diffWon}")

    # 기후환경요금(원미만 절사) : 2,650원
    # 500kWh × 30/30일* = 500kWh(소수 첫째 자리 반올림)
    #   * 전기요금 체계개편 적용일 전·후로 일수계산. 적용일 이후의 일수 반영500kWh × 5.3원 = 2,650원
    def calc_climateWon(self) :
        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        climatePrice = CALC_PARAMETER[pressure]['adjustment'][1] # 기후환경요금 단가
        climateWon = round(energy * climatePrice)
        _LOGGER.debug(f"  기후환경요금:{climateWon}원 = 사용량:{energy}kWh * 기후환경요금단가:{climatePrice}원")
        self._ret['climateWon'] = climateWon

    # 연료비조정액(원미만 절사) : -1,500원
    # 500kWh × -3원 = -1,500원
    # * 연료비조정액은 일수계산 안 함
    def calc_fuelWon(self) :
        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        fuelPrice = CALC_PARAMETER[pressure]['adjustment'][2] # 연료비조정액 단가
        fuelWon = round(energy * fuelPrice)
        _LOGGER.debug(f"  연료비조정액:{fuelWon}원 = 사용량:{energy}kWh * 연료비조정단가:{fuelPrice}원")
        self._ret['fuelWon'] = fuelWon



    # 필수사용량 보장공제
    # 가정용 저압 [200kWh 이하, 최대 2,000원]
    # 가정용 고압, 복지할인시 [200kWh 이하, 2,500원]
    # (기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) - 1000
    def calc_elecBasic(self) :
        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        elecBasicLimit = CALC_PARAMETER[pressure]['elecBasicLimit'] # 최대할인액
        elecBasic = 200
        if (energy <= elecBasic) :
            elecBasicDc = self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['diffWon'] + self._ret['fuelWon'] - 1000
            if elecBasicDc > elecBasicLimit :
                elecBasicDc = elecBasicLimit
            self._ret['elecBasicDc'] = elecBasicDc
            _LOGGER.debug(f"필수사용량 보장공제:{elecBasicDc} = {elecBasicLimit} or 기본요금합:{self._ret['basicWon']}원, 전력량요금합:{self._ret['kwhWon']}원, 환경비용차감:{self._ret['diffWon']}원 - 1000")


    # 200kWh 이하 감액(원미만 절사) = 저압 4,000  고압 2,500
    def calc_elecBasic200(self) :
        energy = self._ret['energy'] # 사용전력
        pressure = self._ret['pressure'] # 계약전력
        elecBasic200Limit = CALC_PARAMETER[pressure]['elecBasic200Limit'] # 최대할인액
        elecBasic = 200
        if (energy <= elecBasic) :
            self._ret['elecBasicDc'] = 0
            elecBasic200Dc = self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['climateWon'] + self._ret['fuelWon']
            if elecBasic200Dc > elecBasic200Limit :
                elecBasic200Dc = elecBasic200Limit
            self._ret['elecBasic200Dc'] = elecBasic200Dc
            _LOGGER.debug(f"200kWh 이하 감액:{elecBasic200Dc} = {elecBasic200Limit} or 기본요금합:{self._ret['basicWon']}원 + 전력량요금합:{self._ret['kwhWon']}원 + 기후환경요금{self._ret['climateWon']} + 연료비조정액:{self._ret['fuelWon']}원")

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
        welfareDcCfg = self._ret['welfareDcCfg'] # 사용전력
        season = self._ret['season']
        if season == 'winter' : # 하계 혹은 기타 시즌 (동계는 기타시즌으로 셋팅)
            season = 'etc'
        dc = CALC_PARAMETER['dc'][season] # 최대할인액
        welfareDc = math.floor(self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['climateWon'] + self._ret['fuelWon'])
        if (welfareDcCfg == 1) : # B1
            if (welfareDc > dc['b1']) :
                welfareDc = dc['b1']
            _LOGGER.debug(f"유공자,장애인할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b1']}")
        elif (welfareDcCfg == 2) :
            welfareDc = welfareDc * dc['b2']
            _LOGGER.debug(f"사회복지시설할인 : {welfareDc} = (전기요금계 - 필수사용량 보장공제 ) x {dc['b2']}, 한도 없음")
        elif (welfareDcCfg == 3) :
            if (welfareDc > dc['b3']) :
                welfareDc = dc['b3']
            _LOGGER.debug(f"기초생활(생계.의료)할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b3']}")
        elif (welfareDcCfg == 4) :
            if (welfareDc > dc['b4']) :
                welfareDc = dc['b4']
            _LOGGER.debug(f"기초생활(주거.교육)할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b4']}")
        elif (welfareDcCfg == 5) :
            if (welfareDc > dc['b5']) :
                welfareDc = dc['b5']
            _LOGGER.debug(f"차사위계층할인 : {welfareDc} = (전기요금계 - 200kWh이하감액 ) or {dc['b5']}")
        self._ret['welfareDc'] = welfareDc

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
        bigfamDcCfg = self._ret['bigfamDcCfg']
        welfareDcCfg = self._ret['welfareDcCfg']
        elecBasic200Dc = self._ret['elecBasic200Dc']
        welfareDc = self._ret['welfareDc']
        season = self._ret['season']
        if season == 'winter' : # 하계 혹은 기타 시즌 (동계는 기타시즌으로 셋팅)
            season = 'etc'
        dc = CALC_PARAMETER['dc'][season] # 최대할인액
        welfareDc_temp = 0
        if (welfareDcCfg >= 2) : # A2
            welfareDc_temp = welfareDc
        kwhWonSum = self._ret['basicWon'] + self._ret['kwhWon'] + self._ret['climateWon'] + self._ret['fuelWon']
        bigfamDc = math.floor((kwhWonSum - elecBasic200Dc - welfareDc_temp) * dc['a2'])
        if (bigfamDcCfg == 1) : # A1
            if (bigfamDc > dc['a1']) :
                bigfamDc = dc['a1']
            _LOGGER.debug(f"대가족 요금할인 : {bigfamDc} = 전기요금계({kwhWonSum} - {elecBasic200Dc} - {welfareDc_temp} x {dc['a1']}, 최대 {dc['a2']}")
        else :
            _LOGGER.debug(f"생명유지장치 : {bigfamDc} = 전기요금계 - {elecBasic200Dc} - {welfareDc_temp} x {dc['a1']}")
        self._ret['bigfamDc'] = bigfamDc

    # 복지할인 중복계산
    # A B 중 큰 금액 적용
    # 차사위계층,기초생활은 중복할인 (A + B)
    def calc_dc(self):
        welfareDcCfg = self._ret['welfareDcCfg']
        bigfamDc = self._ret['bigfamDc']
        welfareDc = self._ret['welfareDc']
        if (welfareDcCfg >= 3) : # 중복할인
            dcValue = bigfamDc + welfareDc
        else :
            if (bigfamDc > welfareDc) :
                self._ret['welfareDc'] = 0
                dcValue = bigfamDc
            else :
                self._ret['bigfamDc'] = 0
                dcValue = welfareDc
            _LOGGER.debug(f'복지할인 {dcValue} = 대가족 요금할인 {bigfamDc} + 복지 요금할인 {welfareDc} 더큰것')


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
        vat = math.floor(elecSumWon * 0.1) # 부가가치세
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
        _LOGGER.debug(f"청구금액:{total}원 = (전기요금계{elecSumWon} + 부가가치세{vat} + 전력산업기반기금{baseFund})")


    def kwh2won(self, energy) :
        
        _LOGGER.debug(f'########### 전기사용량 : {energy}')
        energy = float(energy)
        if energy == 0 :
            self._ret['energy'] = 0.0001
        else :
            self._ret['energy'] = energy

        _LOGGER.debug(f"오늘: {self._ret['today']}, 검침일: {self._ret['checkDay']}")
        
        self.calc_lengthDays()    # 월길이
        self.calc_lengthUseDays() # 상계, 하계 기간
        self.calc_prog()          # 기본요금, 전력량요금
        self.calc_climateWon()    # 기후 환경요금
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



cfg = {
    'pressure' : 'low',
    'checkDay' : 1, # 검침일
    'today' : datetime.datetime(2021,12,22, 1,0,0), # 오늘
    # 'today': datetime.datetime.now(),
    'bigfamDcCfg' : 0, # 대가족 요금할인
    'welfareDcCfg' : 0, # 복지 요금할인
}

K2W = kwh2won_api(cfg)
ret = K2W.kwh2won(20)
# K2W.calc_lengthDays()
# forc = K2W.energy_forecast(17)
# # import pprint
# # pprint.pprint(ret)
