import math
import datetime

# 로그 생성
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
        'basicprice' : [910, 1600, 7300], # 기본요금(원/호)
        # 'kwhprice' : [88.3, 182.9, 275.6], # 전력량 요금(원/kWh)
        'kwhprice' : [93.3, 187.9, 280.6], # 전력량 요금(원/kWh) - 개편전 요금
        'kwhsection': {
            'up' : [0, 200, 400],    # 구간(kWh - 상계)
            'down' : [0, 300, 450]   # 구간(kWh - 하계)(7~8월)
        },
        'adjustment' : [-5, 5.3, -3], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 2000,
        'elecBasic200Limit' : 4000
    },
    'high': {
        'basicprice' : [730, 1260, 6060], # 기본요금(원/호)
        'kwhprice' : [73.3, 142.3, 210.6], # 전력량 요금(원/kWh)
        'kwhsection': {
            'up' : [0, 200, 400],    # 구간(kWh - 상계)
            'down' : [0, 300, 450]   # 구간(kWh - 하계)(7~8월)
        },
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 1500,
        'elecBasic200Limit' : 2500
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

k2w_config = {
    'pressure' : 'low',
    'checkday' : 11, # 검침일
    # 'monthday' : (NOW.month * 100) + NOW.day, # 월일 mmdd
    'monthday' : 711, # 월일 mmdd
    'bigfam_dc' : 0, # 대가족 요금할인
    'welfare_dc' : 0, # 복지 요금할인
}

class kwh2won_api:
    def __init__(self, cfg):
        self._pressure = cfg['pressure']
        self._checkday = cfg['checkday']
        self._monthday = cfg['monthday'] 
        self._bigfam_dc = cfg['bigfam_dc']
        self._welfare_dc = cfg['welfare_dc']
        # self.kwh2won()


    # 예상 사용량
    def energy_forecast(self, energy):
        # 사용일 = (오늘 > 검침일) ? 오늘 - 검침일 : 전달일수 - 검침일 + 오늘
        # 월일수 = (오늘 > 검침일) ? 이번달일수 : 전달일수
        # 시간나누기 = ((사용일-1)*24)+(현재시간+1)
        # 시간곱하기 = 월일수*24
        # 예측 = 에너지 / 시간나누기 * 시간곱하기
        checkday = self._checkday
        if NOW.day > checkday :
            lastday = self.last_day_of_month(NOW)
            lastday = lastday.day
            useday = NOW.day - checkday
        else :
            lastday = NOW - datetime.timedelta(days=NOW.day)
            lastday = lastday.day
            useday = lastday + NOW.day - checkday
        return round(energy / (((useday - 1) * 24) + NOW.hour + 1) * (lastday * 24), 1)

    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)


    # 누진 요금 구하기
    def prog_calc(self, energy,kwhprice,kwhsection):
        won = 0
        section = 0
        for s in [2,1,0]:
            if kwhsection[s] < energy : # 상계금액
                _LOGGER.debug(f'{s+1}단계 금액 : {(energy - kwhsection[s]) * kwhprice[s]}won = {energy - kwhsection[s]}kWh * {kwhprice[s]}won, energy: {energy}')
                won += (energy - kwhsection[s]) * kwhprice[s] # 구간 요금 계산
                energy -= energy - kwhsection[s] # 계산된 구간 용량 빼기
                section += 1 # 누진 단계
        return {'won':won, 'section':section}

    def kwh2won(self, energy) :
        if energy == 0 :
            energy = 0.0001
        # monthday = (NOW.month * 100) + NOW.day
        monthday = self._monthday
        checkday = self._checkday # 검침일

        # basicprice = [910, 1600, 7300] # 기본요금(원/호)
        # kwhprice = [88.3, 182.9, 275.6] # 전력량 요금(원/kWh)
        # # kwhprice = [93.3, 187.9, 280.6] # 전력량 요금(원/kWh) - 개편전 요금
        # kwhsectionUp = [0, 200, 400] # 구간(kWh - 상계)
        # kwhsectionDown = [0, 300, 450] # 구간(kWh - 하계)(7~8월)
        # adjustment = [-5, 5.3, 0] # 환경비용차감 + 기후환경요금 + 연료비조정액
        # # adjustment = [-5, 5.3, -3] # 환경비용차감 + 기후환경요금 + 연료비조정액 - 개편전 요금
        pressure = self._pressure # 저압 'low', 고압 'high'
        basicprice = CALC_PARAMETER[pressure]['basicprice'] # 기본요금(원/호)
        kwhprice = CALC_PARAMETER[pressure]['kwhprice'] # 전력량 요금(원/kWh)
        kwhsection = CALC_PARAMETER[pressure]['kwhsection'] # 구간(kWh - 상계,하계)
        adjustment = CALC_PARAMETER[pressure]['adjustment'] # 환경비용차감 + 기후환경요금 + 연료비조정액
        elecBasicLimit = CALC_PARAMETER[pressure]['elecBasicLimit'] # 
        elecBasic200Limit = CALC_PARAMETER[pressure]['elecBasic200Limit'] # 
        
        season = 'up' # 상계
        dayUp = 0 # 상계일수
        dayDown = 0 # 하계일수 (7,8월)
        DemandUp = 0 # 상계 전력량요금
        DemandDown = 0 # 하계 전력량요금
        progUp = 0 # 누진단계
        progDown = 0
        # BasicCharge = 0 # 기본요금
        UsingCharge = 0 # 전력량요금
        totalCharge = 0 # 최종금액

        # 검침일이 말일일때
        if checkday == 0 :
            lastdate = self.last_day_of_month(NOW)
            checkday = lastdate.day

        adjustValue = math.floor(energy * (adjustment[0] + adjustment[1] + adjustment[2])) # 조정액
        _LOGGER.debug(f'energy {energy}')
        _LOGGER.debug(f'조정액 {adjustValue} = {adjustment[0]} + {adjustment[1]} + {adjustment[2]}')
        _LOGGER.debug(f'월일 {monthday}, 검침일 {checkday}')

        # 누진 계산
        # 상계요금
        prog = self.prog_calc(energy,kwhprice,kwhsection[season])
        DemandUp = math.floor(prog['won'])
        progUp = prog['section']
        self._prog_up = progUp
        _LOGGER.debug(f'상계 요금 : {basicprice[progUp-1]+DemandUp}원 = {progUp}단계, 기본 {basicprice[progUp-1]}원 + 사용 {DemandUp}원')
        DemandUp += basicprice[progUp-1] # 기본요금 더하기
        if (monthday > checkday + 600) and (monthday <= checkday + 900) :
            season = 'down'
        if season == 'down' : # 하계(7~8월), 상하계 사용 일수 계산
            # 하계요금
            prog = self.prog_calc(energy,kwhprice,kwhsection[season])
            DemandDown = prog['won']
            progDown = prog['section']
            self._prog_down = progDown
            _LOGGER.debug(f'하계 요금 : {basicprice[progDown-1]+DemandDown}원 = {progDown}단계, 기본 {basicprice[progDown-1]}원 + 사용 {DemandDown}원')
            DemandDown += basicprice[progDown-1]

            if monthday <= checkday + 700 : # 검침일이 7월일때 
                dayUp = 30 - checkday
                dayDown = checkday
            elif monthday <= checkday + 800 : # 검침일이 8월일때 
                dayUp = 0
                dayDown = 31
            else : # 검침일이 9월일때 
                dayUp = checkday
                dayDown = 31 - checkday
            _LOGGER.debug(f'상계 일수 {dayUp}일, 일계요금 {math.floor(DemandUp * dayUp / (dayUp+dayDown))}')
            _LOGGER.debug(f'하계 일수 {dayDown}일, 일계요금 {math.floor(DemandDown * dayDown / (dayUp+dayDown))}')
            UsingCharge = math.floor(DemandUp * dayUp / (dayUp+dayDown)) + math.floor(DemandDown * dayDown / (dayUp+dayDown))
        else : # 상계
            _LOGGER.debug(f'상계 일수 *일, 일계요금 {DemandUp}원')
            _LOGGER.debug(f'하계 일수 0일, 일계요금 0원')
            UsingCharge = DemandUp

        iBigFamBoolean = self._bigfam_dc # 대가족 요금할인
        iWelfareDcBoolean = self._welfare_dc # 복지 요금할인

        dcValue = 0 # 최종 할인요금
        elecBasicValue = 0 # 필수사용량 보장공제
        elecBasic200Value = 0 # 200kWh 이하 감액

        # 필수사용량 보장공제
        # 가정용 저압 [200kWh 이하, 최대 2,000원]
        # 가정용 고압, 복지할인시 [200kWh 이하, 2,500원]
        # (기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) - 1000
        elecBasic = 200
        if (energy <= elecBasic) :
            elecBasicValue = UsingCharge + adjustValue - 1000
            if elecBasicValue > elecBasicLimit :
                elecBasicValue = elecBasicLimit
                _LOGGER.debug(f'필수사용량 보장공제 : {elecBasicValue}')


        iWelfareDcValue = 0
        iBigFamValue = 0
        if (iBigFamBoolean or iWelfareDcBoolean) :
            dc = CALC_PARAMETER['dc'][season]

            # 복지할인
            # 필수사용량 보장공제 = 0
            # 200kWh 이하 감액(원미만 절사) = 저압 4,000  고압 2,500
            if (energy <= elecBasic) :
                elecBasicValue = 0
                elecBasic200Value = UsingCharge + adjustValue
                if elecBasic200Value > elecBasic200Limit :
                    elecBasic200Value = elecBasic200Limit
                _LOGGER.debug(f'200kWh 이하 감액 : {elecBasic200Value}')

            # 복지 요금할인
            # B1 : 독립유공자,국가유공자,5.18민주유공자,장애인 (16,000원 한도)
            # B2 : 사회복지시설 (전기요금계((기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) － 필수사용량 보장공제) x 30%, 한도 없음)
            # B3 : 기초생활(생계.의료) (16,000원 한도) + 중복할인
            # B4 : 기초생활(주거.교육) (10,000원 한도) + 중복할인
            # B5 : 차사위계층 (8,000원 한도) + 중복할인
            # B  : 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인)
            # B2 :              전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인 － 필수사용량 보장공제)
            if (iWelfareDcBoolean) :
                iWelfareDcValue = math.floor(UsingCharge + adjustValue)
                if (iWelfareDcBoolean == 1) : # B1
                    if (iWelfareDcValue > dc['b1']) :
                        iWelfareDcValue = dc['b1']
                    _LOGGER.debug(f"유공자,장애인 : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or {dc['b1']}")
                elif (iWelfareDcBoolean == 2) :
                    iWelfareDcValue = math.floor((UsingCharge + adjustValue) * dc['b2'])
                    _LOGGER.debug(f"사회복지시설 : {iWelfareDcValue} = (전기요금계 - 필수사용량 보장공제 ) x {dc['b2']}, 한도 없음")
                elif (iWelfareDcBoolean == 3) :
                    if (iWelfareDcValue > dc['b3']) :
                        iWelfareDcValue = dc['b3']
                    _LOGGER.debug(f"기초생활(생계.의료) : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or {dc['b3']}")
                elif (iWelfareDcBoolean == 4) :
                    if (iWelfareDcValue > dc['b4']) :
                        iWelfareDcValue = dc['b4']
                    _LOGGER.debug(f"기초생활(주거.교육) : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or {dc['b4']}")
                elif (iWelfareDcBoolean == 5) :
                    if (iWelfareDcValue > dc['b5']) :
                        iWelfareDcValue = dc['b5']
                    _LOGGER.debug(f"차사위계층 : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or {dc['b5']}")

            # 대가족 요금할인
            # A1 : 5인이상 가구,출산가구,3자녀이상 가구 (16,000원 한도)
            # A2 : 생명유지장치 (한도 없음)
            # 전기요금계((기본요금 ＋ 전력량요금 － 필수사용량 보장공제 ＋ 기후환경요금 ± 연료비조정액) － 200kWh이하감액) x 30% = 대가족 요금할인
            if (iBigFamBoolean) :
                iWelfareDcValue_temp = 0
                if (iWelfareDcBoolean >= 2) : # A2
                    iWelfareDcValue_temp = iWelfareDcValue
                iBigFamValue = math.floor((UsingCharge + adjustValue - elecBasic200Value - iWelfareDcValue_temp) * dc['a2'])
                if (iBigFamBoolean == 1) : # A1
                    if (iBigFamValue > dc['a1']) :
                        iBigFamValue = dc['a1']
                    _LOGGER.debug(f"대가족 요금할인 : {iBigFamValue} = 전기요금계({UsingCharge} + {adjustValue}) - {elecBasic200Value} - {iWelfareDcValue_temp} x {dc['a1']}, 최대 {dc['a2']}")
                else :
                    _LOGGER.debug(f"생명유지장치 : {iBigFamValue} = 전기요금계 - {elecBasic200Value} - {iWelfareDcValue_temp} x {dc['a1']}")

            # A B 중 큰 금액 적용
            # 차사위계층,기초생활은 중복할인 (A + B)
            if (iWelfareDcBoolean >= 3) : # 중복할인
                dcValue = iBigFamValue + iWelfareDcValue
                _LOGGER.debug(f'복지할인 {dcValue} = 대가족 요금할인 {iBigFamValue} + 복지 요금할인 {iWelfareDcValue}')
            else :
                if (iBigFamValue > iWelfareDcValue) :
                    dcValue = iBigFamValue
                else :
                    dcValue = iWelfareDcValue 
                _LOGGER.debug(f'복지할인 {dcValue} = 대가족 요금할인 {iBigFamValue} or 복지 요금할인 {iWelfareDcValue} 더큰것')

        _LOGGER.debug(f'최종 요금 : {round((UsingCharge + adjustValue - elecBasicValue - elecBasic200Value - dcValue) * 1.137)}원 = ((사용요금 {UsingCharge} + (조정액 {adjustValue}) - 필수사용량 보장공제{elecBasicValue} - 200kWh 이하 감액{elecBasic200Value} - 복지할인 {dcValue}) * 부가세,기금1.137)')
        totalCharge =  (UsingCharge + adjustValue - elecBasicValue - elecBasic200Value - dcValue) * 1.137

        if (totalCharge < 0) :
            totalCharge = 0
        # elif (energy == 0) : # 사용량이 0 이면 50% 할인
        #     totalCharge = int(totalCharge/2)
        totalCharge =  math.floor(totalCharge/10)*10
        _LOGGER.debug(f'{totalCharge}')
        return {
            'won': totalCharge,
            'progUp': progUp,
            'progDown': progDown,
            'UsingCharge': UsingCharge,
            'adjustValue': adjustValue,
            'elecBasicValue': elecBasicValue,
            'elecBasic200Value': elecBasic200Value,
            'iBigFamValue': iBigFamValue,
            'iWelfareDcValue': iWelfareDcValue,
        }
        

K2W = kwh2won_api(k2w_config)
K2W.kwh2won(300)