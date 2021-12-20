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


NOW = datetime.datetime.now()

CALC_PARAMETER = {
    'low': {
        'basicPrice' : [910, 1600, 7300],    # 기본요금(원/호)
        # 'kwhPrice' : [88.3, 182.9, 275.6], # 전력량 요금(원/kWh)
        'kwhPrice' : [93.3, 187.9, 280.6],   # 전력량 요금(원/kWh) - 개편전 요금
        'kwhSection': {
            'up' : [200, 400, 10000],    # 구간(kWh - 상계)
            'down' : [300, 450, 10000]   # 구간(kWh - 하계)(7~8월)
        },
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 2000,     # 필수사용공제
        'elecBasic200Limit' : 4000   # 200kWh이하 감액
    },
    'high': {
        'basicPrice' : [730, 1260, 6060],  # 기본요금(원/호)
        'kwhPrice' : [73.3, 142.3, 210.6], # 전력량 요금(원/kWh)
        'kwhSection': {
            'up' : [200, 400, 10000],   # 구간(kWh - 상계)
            'down' : [300, 450, 10000], # 구간(kWh - 하계)(7~8월)
        },
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 1500,     # 필수사용공제
        'elecBasic200Limit' : 2500   # 200kWh이하 감액
    },
    'dc': {
        'up': {
            'a1': 16000, # 5인이상 가구,출산가구,3자녀이상 가구
            'a2': 0.3,   # 생명유지장치
            'b1': 16000, # 독립유공자,국가유공자,5.18민주유공자,장애인 
            'b2': 0.3,   # 사회복지시설
            'b3': 16000, # 기초생활(생계.의료)
            'b4': 10000, # 기초생활(주거.교육)
            'b5': 8000,  # 차사위계층
        },
        'down': {
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


ret = {
    'energy': 0,     # 사용량
    'pressure' : 'low',
    'checkDay' : 10, # 검침일
    'today' : datetime.datetime(2022,7,10, 1,0,0), # 오늘
    # 'today': NOW,
    'bigfamDcCfg' : 2, # 대가족 요금할인
    'welfareDcCfg' : 5, # 복지 요금할인
    'monthDays': 0, # 월일수
    'season': 'up',
    'up' : {
        'energy': 0,     # 사용량
        'basicWon': 0,   # 기본요금
        'kwhWon': 0,     # 전력량요금
        'diffWon': 0,    # 환경비용차감
        'useDays': 0,    # 월사용일
        'kwhStep': 0,    # 누진단계
    },
    'down' : {
        'energy': 0,     # 사용량
        'basicWon': 0,   # 기본요금
        'kwhWon': 0,     # 전력량요금
        'diffWon': 0,    # 환경비용차감
        'useDays': 0,    # 월사용일
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

# ==============================================
# 기본요금(원미만 절사) basicWon
# 환경비용차감(원미만 절사) diffWon = 사용량 energy * 단가 adjustment[0]
# 기후환경요금(원미만 절사) climateWon = 사용량 energy (소수 첫째 자리 반올림) * 단가 adjustment[1]
# 연료비조정액(원미만 절사) fuelWon = 사용량 energy * 단가 adjustment[2]
# 월일수 monthDays = 30
# 6월사용일 useDays = 10
# 7월사용일 useDays_H = 20


# 전력량요금(원미만 절사) kwhWon = ( (사용량 energy / 월일수 monthDays * 6월사용일 useDays['up'] ) * 6월단가 ) + ( (사용량 / 월일수 * 7월사용일) * 7월단가 ) + 환경비용차감 diffWon
# : 18,660원
# 6월 1단계 : 67kWh* ×93.3원** ＝ 6,251.1원
#   * 67kWh - 0kWh = 67kWh
#   ** 개정 전 단가
# (하계 133 kWh)
# ·1단계 : 133kWh* ×93.3원** ＝ 12,408.9원
#   * 133kWh - 0kWh = 133kWh
#   ** 개정 전 단가


# 환경비용차감(원미만 절사) : 200kWh × -5원 = -1,000원
# energy * 

# 전기요금계 = Demand_Qty


# 필수사용량보장공제
# 6월 계산분 : 303.3원 + 5,916.1원 + 355.1원 － 201원 － 1,333.3원 ＞ 333.3원 (감액 후 최저요금)
# 7월 계산분 : 606.7원 + 11,743.9원 + 704.9원 － 399원 － 1,333.3원 ＞ 666.7원 (감액 후 최저요금)
# (기본요금 + 전력량요금 + 기후환경욕금 + 연료비조정액 + 필수사용량제공공재) / 월일수 * 6월사용일 > (1000 월일수 * 6월사용일 )
# (기본요금 + 전력량요금 + 기후환경욕금 + 연료비조정액 + 필수사용량제공공재) / 월일수 * 7월사용일 > (1000 월일수 * 7월사용일 )

# 전기요금계 = (기본요금 ＋ 전력량요금 － 필수사용량보장공제 ＋ 기후환경요금 + 연료비조정액)
# : 910원 ＋ 17,660원 － 2,666원 ＋ 1,060원 － 600원 ＝ 16,364원

# 부가가치세(원미만 4사 5입) =  전기요금계 * 0.1
#  : 16,364원 × 0.1 ＝ 1,636원

# 전력산업기반기금(10원미만 절사) = 전기요금계 * 단가
#  : 16,364원 × 0.037 ＝ 600원

# 청구금액(10원미만 절사) = (전기요금계 ＋ 부가가치세 ＋ 전력산업기반기금)
# : 16,364원 ＋ 1,636원 ＋ 600원 ＝ 18,600원

class kwh2won_api:
    def __init__(self, cfg):
        self._cfg = cfg
        # self.kwh2won()


    # 예상 사용량
    def energy_forecast(self):
        # 사용일 = (오늘 > 검침일) ? 오늘 - 검침일 : 전달일수 - 검침일 + 오늘
        # 월일수 = (오늘 > 검침일) ? 이번달일수 : 전달일수
        # 시간나누기 = ((사용일-1)*24)+(현재시간+1)
        # 시간곱하기 = 월일수*24
        # 예측 = 에너지 / 시간나누기 * 시간곱하기
        energy = self._cfg['energy']
        checkDay = self._cfg['checkDay']
        if NOW.day > checkDay :
            lastday = self.last_day_of_month(NOW)
            lastday = lastday.day
            useday = NOW.day - checkDay
        else :
            lastday = NOW - datetime.timedelta(days=NOW.day)
            lastday = lastday.day
            useday = lastday + NOW.day - checkDay
        return round(energy / (((useday - 1) * 24) + NOW.hour + 1) * (lastday * 24), 1)

    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)


    # 월별 사용일 구하기
    def calc_lengthDays(self) :
        today = self._cfg['today']
        checkDay = self._cfg['checkDay']
        if today.day > checkDay : # 오늘이 검침일보다 크면
            lastday = self.last_day_of_month(today) # 달의 마지막일이 전체 길이
            monthDays = lastday.day
        else : # 오늘이 검칠일과 같거나 작으면
            lastday = today - datetime.timedelta(days=today.day) # 전달의 마지막일이 전체 길이
            monthDays = lastday.day
        self._cfg['monthDays'] = monthDays
        _LOGGER.debug(f'월일수: {monthDays}')


    # 월별 상계, 하계 일수 구하기
    def calc_lengthUseDays(self) :
        checkDay = self._cfg['checkDay']
        today = int(self._cfg['today'].strftime('%m%d'))
        # 하계(7~8월), 상하계 사용 일수 계산
        if (today > checkDay + 600) and (today <= checkDay + 900) :
            season = 'down'
            # 하계
            if today <= checkDay + 700 : # 검침일이 7월일때 
                up = 30 - checkDay
                down = checkDay
            elif today <= checkDay + 800 : # 검침일이 8월일때 
                up = 0
                down = 31
            else : # 검침일이 9월일때 
                up = checkDay
                down = 31 - checkDay
        else : # 상계
            season = 'up'
            up = self._cfg['monthDays']
            down = 0

        self._cfg['season'] = season
        self._cfg['up']['useDays'] = up
        self._cfg['down']['useDays'] = down
        _LOGGER.debug(f'상계일수: {up}, 하계일수: {down}, 계산시즌: {season}')


    # 월간 500kWh 사용시 전기요금 계산(주거용)
    # 기본요금(원미만 절사) : 7,300원내역닫기
    #   (기타계절 적용시 3단계, 사용량 400kWh 초과 구간)
    #   (하계 적용시 3단계, 사용량 450kWh 초과 구간)
    # 전력량요금(원미만 절사) : 72,310원
    # : 개편전요금 74,810원 － 환경비용차감 2,500원내역닫기
    # 개편전요금(원미만 절사) : 74,810원
    # (기타계절 167 kWh)
    # ·1단계 : 67kWh* ×93.3 원** ＝ 6,251.1원
    #   * 200kWh ×10일 /30일 = 67kWh
    #   ** 개정 전 단가
    # ·2단계 : 67kWh* ×187.9 원** ＝ 12,589.3원
    #   * 200kWh ×10일 /30일 = 67kWh
    #   ** 개정 전 단가
    # ·3단계 : 33kWh* ×280.6원** ＝ 9,259.8원
    #   * 167kWh - 134kWh = 33kWh
    #   ** 개정 전 단가
    # (하계 333 kWh)
    # ·1단계 : 200kWh* ×93.3 원** ＝ 18,660원
    #   * 300kWh ×20일 /30일 = 200kWh
    #   ** 개정 전 단가
    # ·2단계 : 100kWh* ×187.9 원** ＝ 18,790원
    #   * 150kWh ×20일 /30일 = 100kWh
    #   ** 개정 전 단가
    # ·3단계 : 33kWh* ×280.6원** ＝ 9,259.8원
    #   * 333kWh - 300kWh = 33kWh
    #   ** 개정 전 단가
    # 환경비용차감(원미만 절사) : 500kWh × -5원 = -2,500원
    def calc_prog(self):

        energy = self._cfg['energy'] # 사용전력
        pressure = self._cfg['pressure'] # 계약전력
        basicPrice = CALC_PARAMETER[pressure]['basicPrice'] # 기본요금(원/호)
        kwhPrice = CALC_PARAMETER[pressure]['kwhPrice'] # 전력량 단가(원/kWh)
        diffPrice = CALC_PARAMETER[pressure]['adjustment'][0] # 환경비용차감 단가
        monthDays = self._cfg['monthDays'] # 월일수
        basicWonSum = 0
        kwhWonSum = 0

        _LOGGER.debug(f"누진요금구하기 ===== ")
        # 시즌 요금 구하기
        for season in ['up','down'] :
            seasonDays = self._cfg[season]['useDays'] # 사용일수
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
                _LOGGER.debug(f"    {kwhStep}단계, 구간에너지 : {stepEnergy}, 구간전력량요금 : {kwhWon}원 = ({stepEnergy}kWh * {seasonDays}d / {monthDays}d):{round(stepEnergy*seasonDays/monthDays)}kWh * {kwhPrice[kwhStep-1]}원") # 구간 요금 계산
            basicWon = math.floor(basicPrice[kwhStep-1] * seasonDays / monthDays)
            basicWonSum += basicWon
            self._cfg[season]['basicWon'] = basicWon
            self._cfg[season]['kwhWon'] = kwhWonSum
            self._cfg[season]['kwhStep'] = kwhStep
            _LOGGER.debug(f"    시즌기본요금:{math.floor(basicWon)}원, 시즌전력량요금:{kwhWonSum}원")
        basicWonSum = math.floor(basicWonSum)
        diffWon = energy * diffPrice # 환경비용차감
        kwhWon = math.floor(kwhWonSum + diffWon)
        self._cfg['kwhWon'] = kwhWon
        self._cfg['basicWon'] = basicWonSum
        self._cfg['diffWon'] = diffWon
        _LOGGER.debug(f"  기본요금합:{basicWonSum}원, 전력량요금합:{math.floor(kwhWonSum)}원, 환경비용차감:{diffWon}원 = 사용량:{energy}kWh * 환경비요차감단가:{diffPrice}원")
        _LOGGER.debug(f"  전력량요금:{kwhWon}원 = 전력량요금합:{math.floor(kwhWonSum)} + 환경비용차감:{diffWon}")

    # 기후환경요금(원미만 절사) : 2,650원
    # 500kWh × 30/30일* = 500kWh(소수 첫째 자리 반올림)
    #   * 전기요금 체계개편 적용일 전·후로 일수계산. 적용일 이후의 일수 반영500kWh × 5.3원 = 2,650원
    def calc_climateWon(self) :
        energy = self._cfg['energy'] # 사용전력
        pressure = self._cfg['pressure'] # 계약전력
        climatePrice = CALC_PARAMETER[pressure]['adjustment'][1] # 기후환경요금 단가
        climateWon = round(energy * climatePrice)
        _LOGGER.debug(f"  기후환경요금:{climateWon}원 = 사용량:{energy}kWh * 기후환경요금단가:{climatePrice}원")
        self._cfg['climateWon'] = climateWon

    # 연료비조정액(원미만 절사) : -1,500원
    # 500kWh × -3원 = -1,500원
    # * 연료비조정액은 일수계산 안 함
    def calc_fuelWon(self) :
        energy = self._cfg['energy'] # 사용전력
        pressure = self._cfg['pressure'] # 계약전력
        fuelPrice = CALC_PARAMETER[pressure]['adjustment'][2] # 기후환경요금 단가
        fuelWon = round(energy * fuelPrice)
        _LOGGER.debug(f"  연료비조정액:{fuelWon}원 = 사용량:{energy}kWh * 연료비조정단가:{fuelPrice}원")
        self._cfg['fuelWon'] = fuelWon



    # 필수사용량 보장공제
    # 가정용 저압 [200kWh 이하, 최대 2,000원]
    # 가정용 고압, 복지할인시 [200kWh 이하, 2,500원]
    # (기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) - 1000
    def calc_elecBasic(self) :
        energy = self._cfg['energy'] # 사용전력
        pressure = self._cfg['pressure'] # 계약전력
        elecBasicLimit = CALC_PARAMETER[pressure]['elecBasicLimit'] # 최대할인액
        elecBasic = 200
        if (energy <= elecBasic) :
            elecBasicDc = self._cfg['basicWon'] + self._cfg['kwhWon'] + self._cfg['diffWon'] + self._cfg['fuelWon'] - 1000
            if elecBasicDc > elecBasicLimit :
                elecBasicDc = elecBasicLimit
            self._cfg['elecBasicDc'] = elecBasicDc
            _LOGGER.debug(f"필수사용량 보장공제:{elecBasicDc} = {elecBasicLimit} or 기본요금합:{self._cfg['basicWon']}원, 전력량요금합:{self._cfg['kwhWon']}원, 환경비용차감:{self._cfg['diffWon']}원 - 1000")


    def calc_elecBasic200(self) :
        energy = self._cfg['energy'] # 사용전력
        pressure = self._cfg['pressure'] # 계약전력
        elecBasic200Limit = CALC_PARAMETER[pressure]['elecBasic200Limit'] # 최대할인액
        elecBasic = 200
        if (energy <= elecBasic) :
            self._cfg['elecBasicDc'] = 0
            elecBasic200Dc = self._cfg['basicWon'] + self._cfg['kwhWon'] + self._cfg['climateWon'] + self._cfg['fuelWon']
            if elecBasic200Dc > elecBasic200Limit :
                elecBasic200Dc = elecBasic200Limit
            self._cfg['elecBasic200Dc'] = elecBasic200Dc
            _LOGGER.debug(f"200kWh 이하 감:{elecBasic200Dc} = {elecBasic200Limit} or 기본요금합:{self._cfg['basicWon']}원 + 전력량요금합:{self._cfg['kwhWon']}원 + 기후환경요금{self._cfg['climateWon']} + 연료비조정액:{self._cfg['fuelWon']}원")

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
        welfareDcCfg = self._cfg['welfareDcCfg'] # 사용전력
        season = self._cfg['season']
        dc = CALC_PARAMETER['dc'][season] # 최대할인액
        welfareDc = math.floor(self._cfg['basicWon'] + self._cfg['kwhWon'] + self._cfg['climateWon'] + self._cfg['fuelWon'])
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
        self._cfg['welfareDc'] = welfareDc

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
        bigfamDcCfg = self._cfg['bigfamDcCfg']
        welfareDcCfg = self._cfg['welfareDcCfg']
        elecBasic200Dc = self._cfg['elecBasic200Dc']
        welfareDc = self._cfg['welfareDc']
        season = self._cfg['season']
        dc = CALC_PARAMETER['dc'][season] # 최대할인액
        welfareDc_temp = 0
        if (welfareDcCfg >= 2) : # A2
            welfareDc_temp = welfareDc
        kwhWonSum = self._cfg['basicWon'] + self._cfg['kwhWon'] + self._cfg['climateWon'] + self._cfg['fuelWon']
        bigfamDc = math.floor((kwhWonSum - elecBasic200Dc - welfareDc_temp) * dc['a2'])
        if (bigfamDcCfg == 1) : # A1
            if (bigfamDc > dc['a1']) :
                bigfamDc = dc['a1']
            _LOGGER.debug(f"대가족 요금할인 : {bigfamDc} = 전기요금계({kwhWonSum} - {elecBasic200Dc} - {welfareDc_temp} x {dc['a1']}, 최대 {dc['a2']}")
        else :
            _LOGGER.debug(f"생명유지장치 : {bigfamDc} = 전기요금계 - {elecBasic200Dc} - {welfareDc_temp} x {dc['a1']}")
        self._cfg['bigfamDc'] = bigfamDc

    # 복지할인 중복계산
    # A B 중 큰 금액 적용
    # 차사위계층,기초생활은 중복할인 (A + B)
    def calc_dc(self):
        welfareDcCfg = self._cfg['welfareDcCfg']
        bigfamDc = self._cfg['bigfamDc']
        welfareDc = self._cfg['welfareDc']
        if (welfareDcCfg >= 3) : # 중복할인
            dcValue = bigfamDc + welfareDc
        else :
            if (bigfamDc > welfareDc) :
                self._cfg['welfareDc'] = 0
                dcValue = bigfamDc
            else :
                self._cfg['bigfamDc'] = 0
                dcValue = welfareDc
            _LOGGER.debug(f'복지할인 {dcValue} = 대가족 요금할인 {bigfamDc} + 복지 요금할인 {welfareDc} 더큰것')


    # 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액)
    # :7,300원 ＋ 72,310원 ＋ 2,650원 － 1,500원 ＝ 80,760원
    # 부가가치세(원미만 4사 5입) : 80,760원 × 0.1 ＝ 8,076원
    # 전력산업기반기금(10원미만 절사) : 80,760원 × 0.037 ＝ 2,980원
    # 청구금액(전기요금계 ＋ 부가가치세 ＋ 전력산업기반기금)
    # : 80,760원 ＋ 8,076원 ＋ 2,980원 ＝ 91,810원(10원미만 절사)
    def calc_total(self) :
        basicWon = self._cfg['basicWon']   # 기본요금
        kwhWon = self._cfg['kwhWon']     # 전력량요금
        # diffWon = self._cfg['diffWon']    # 환경비용차감
        climateWon = self._cfg['climateWon'] # 기후환경요금
        fuelWon = self._cfg['fuelWon']    # 연료비조정액
        elecBasicDc = self._cfg['elecBasicDc'] # 필수사용량보장공제
        elecBasic200Dc = self._cfg['elecBasic200Dc'] # 200kWh이하 감액
        bigfamDc = self._cfg['bigfamDc']   # 대가족 요금할인
        welfareDc = self._cfg['welfareDc']  # 복지 요금할인
        # 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액)
        elecSumWon = basicWon + kwhWon - elecBasicDc + climateWon + fuelWon - elecBasic200Dc - bigfamDc - welfareDc # 전기요금계
        vat = math.floor(elecSumWon * 0.1) # 부가가치세
        baseFund = math.floor(elecSumWon * 0.037 /10)*10 # 전력산업기금
        total = math.floor((elecSumWon + vat + baseFund) /10)*10 # 청구금액
        self._cfg['elecSumWon'] = elecSumWon
        self._cfg['vat'] = vat # 부가가치세
        self._cfg['baseFund'] = baseFund # 전력산업기반기금
        self._cfg['total'] = total # 청구금액
        _LOGGER.debug(f"전기요금계{elecSumWon} = 기본요금{basicWon} + 전력량요금{kwhWon} - 필수사용량 보장공제{elecBasicDc} + 기후환경요금{climateWon} + 연료비조정액{fuelWon} - 200kWh이하 감액{elecBasic200Dc} - 대가족할인{bigfamDc} - 복지할인{welfareDc}")
        _LOGGER.debug(f"청구금액:{total}원 = (전기요금계{elecSumWon} + 부가가치세{vat} + 전력산업기반기금{baseFund})")


    def kwh2won(self, energy) :
        
        _LOGGER.debug(f'전기사용량 : {energy}')

        if energy == 0 :
            self._cfg['energy'] = 0.0001
        else :
            self._cfg['energy'] = energy

        # self._cfg['today'] = datetime.datetime(2021,11,20, 1,0,0) # 오늘
        _LOGGER.debug(f"오늘: {self._cfg['today']}, 검침일: {self._cfg['checkDay']}")
        
        self.calc_lengthDays()    # 월길이
        self.calc_lengthUseDays() # 상계, 하계 기간
        self.calc_prog()          # 기본요금, 전력량요금
        self.calc_climateWon()    # 기후 환경요금
        self.calc_fuelWon()       # 연료비조정액

        if (self._cfg['bigfamDcCfg'] or self._cfg['welfareDcCfg']) :
            self.calc_elecBasic200() # 200kWh 이하 감액
            if self._cfg['welfareDcCfg']:
                self.calc_welfareDc() # 복지할인
            if self._cfg['bigfamDcCfg']:
                self.calc_bigfamDc()  # 대가족할인
            self.calc_dc() # 중복할인 혹은 큰거
        else : 
            self.calc_elecBasic()    # 필수사용량 보장공제
            

        self.calc_total()         # 청구금액
        return self._cfg


        

K2W = kwh2won_api(ret)
ret = K2W.kwh2won(500)
import pprint
pprint.pprint(ret)
