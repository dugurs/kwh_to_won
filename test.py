



import math
import datetime

NOW = datetime.datetime.now()

CALC_PARAMETER = {
    'low': {
        'basicprice' : [910, 1600, 7300], # 기본요금(원/호)
        # 'kwhprice' : [88.3, 182.9, 275.6], # 전력량 요금(원/kWh)
        'kwhprice' : [93.3, 187.9, 280.6], # 전력량 요금(원/kWh) - 개편전 요금
        'kwhsectionUp' : [0, 200, 400], # 구간(kWh - 상계)
        'kwhsectionDown' : [0, 300, 450], # 구간(kWh - 하계)(7~8월)
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 2000,
        'elecBasic200Limit' : 4000
    },
    'high': {
        'basicprice' : [730, 1260, 6060], # 기본요금(원/호)
        'kwhprice' : [73.3, 142.3, 210.6], # 전력량 요금(원/kWh)
        'kwhsectionUp' : [0, 200, 400], # 구간(kWh - 상계)
        'kwhsectionDown' : [0, 300, 450], # 구간(kWh - 하계)(7~8월)
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 1500,
        'elecBasic200Limit' : 2500
    },
}

k2w_config = {
    'energy' : 316,
    'pressure' : 'low',
    'checkday' : 25, # 검침일
    'monthday' : 1215, # 월일 mmdd
    'bigfam_dc' : 1, # 대가족 요금할인
    'welfare_dc' : 0, # 복지 요금할인
}

class kwh2won:
    def __init__(self, cfg):
        self._energy = cfg['energy'] 
        self._pressure = cfg['pressure']
        self._checkday = cfg['checkday']
        self._monthday = cfg['monthday'] 
        self._bigfam_dc = cfg['bigfam_dc']
        self._welfare_dc = cfg['welfare_dc']
        self.kwh2won()


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
                print(f'{s+1}단계 금액 : {(energy - kwhsection[s]) * kwhprice[s]}won = {energy - kwhsection[s]}kWh * {kwhprice[s]}won, energy: {energy}')
                won += (energy - kwhsection[s]) * kwhprice[s] # 구간 요금 계산
                energy -= energy - kwhsection[s] # 계산된 구간 용량 빼기
                section += 1 # 누진 단계
        return {'won':won, 'section':section}

    def kwh2won(self) :
        # monthday = (NOW.month * 100) + NOW.day
        energy = self._energy
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
        kwhsectionUp = CALC_PARAMETER[pressure]['kwhsectionUp'] # 구간(kWh - 상계)
        kwhsectionDown = CALC_PARAMETER[pressure]['kwhsectionDown'] # 구간(kWh - 하계)(7~8월)
        adjustment = CALC_PARAMETER[pressure]['adjustment'] # 환경비용차감 + 기후환경요금 + 연료비조정액
        elecBasicLimit = CALC_PARAMETER[pressure]['elecBasicLimit'] # 
        
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
        print(f'energy {energy}')
        print(f'조정액 {adjustValue} = {adjustment[0]} + {adjustment[1]} + {adjustment[2]}')
        print(f'월일 {monthday}, 검침일 {checkday}')

        # 누진 계산
        # 상계요금
        prog = self.prog_calc(energy,kwhprice,kwhsectionUp)
        DemandUp = math.floor(prog['won'])
        progUp = prog['section']
        self._prog_up = progUp
        print(f'상계 요금 : {basicprice[progUp-1]+DemandUp}원 = {progUp}단계, 기본 {basicprice[progUp-1]}원 + 사용 {DemandUp}원')
        DemandUp += basicprice[progUp-1] # 기본요금 더하기

        if (monthday > checkday + 600) and (monthday <= checkday + 900) : # 하계(7~8월), 상하계 사용 일수 계산
            # 하계요금
            prog = self.prog_calc(energy,kwhprice,kwhsectionDown)
            DemandDown = prog['won']
            progDown = prog['section']
            self._prog_down = progDown
            print(f'하계 요금 : {basicprice[progDown-1]+DemandDown}원 = {progDown}단계, 기본 {basicprice[progDown-1]}원 + 사용 {DemandDown}원')
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
            print(f'상계 일수 {dayUp}일, 일계요금 {math.floor(DemandUp * dayUp / (dayUp+dayDown))}')
            print(f'하계 일수 {dayDown}일, 일계요금 {math.floor(DemandDown * dayDown / (dayUp+dayDown))}')
            UsingCharge = math.floor(DemandUp * dayUp / (dayUp+dayDown)) + math.floor(DemandDown * dayDown / (dayUp+dayDown))
        else : # 상계
            print(f'상계 일수 *일, 일계요금 {DemandUp}원')
            print(f'하계 일수 0일, 일계요금 0원')
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
                print(f'필수사용량 보장공제 : {elecBasicValue}')


        if (iBigFamBoolean or iWelfareDcBoolean) :
            # 복지할인
            # 필수사용량 보장공제 = 0
            # 200kWh 이하 감액(원미만 절사) = 저압 4,000  고압 2,500
            if (energy <= elecBasic) :
                elecBasicValue = 0
                elecBasic200Value = UsingCharge + adjustValue
                if elecBasic200Value > elecBasic200Limit :
                    elecBasic200Value = elecBasic200Limit
                print(f'200kWh 이하 감액 : {elecBasic200Value}')

            # 복지 요금할인
            # B1 : 독립유공자,국가유공자,5.18민주유공자,장애인 (16,000원 한도)
            # B2 : 사회복지시설 (전기요금계((기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) － 필수사용량 보장공제) x 30%, 한도 없음)
            # B3 : 기초생활(생계.의료) (16,000원 한도) + 중복할인
            # B4 : 기초생활(주거.교육) (10,000원 한도) + 중복할인
            # B5 : 차사위계층 (8,000원 한도) + 중복할인
            # B  : 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인)
            # B2 :              전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인 － 필수사용량 보장공제)
            iWelfareDcValue = 0
            if (iWelfareDcBoolean) :
                iWelfareDcValue = math.floor(UsingCharge + adjustValue)
                if (iWelfareDcBoolean == 1) : # B1
                    if (iWelfareDcValue > 16000) :
                        iWelfareDcValue = 16000
                    print(f'유공자,장애인 : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 16,000')
                elif (iWelfareDcBoolean == 2) :
                    iWelfareDcValue = math.floor((UsingCharge + adjustValue) * 0.3)
                    print(f'사회복지시설 : {iWelfareDcValue} = (전기요금계 - 필수사용량 보장공제 ) x 30%, 한도 없음')
                elif (iWelfareDcBoolean == 3) :
                    if (iWelfareDcValue > 16000) :
                        iWelfareDcValue = 16000
                    print(f'기초생활(생계.의료) : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 16,000')
                elif (iWelfareDcBoolean == 4) :
                    if (iWelfareDcValue > 10000) :
                        iWelfareDcValue = 10000
                    print(f'기초생활(주거.교육) : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 10,000')
                elif (iWelfareDcBoolean == 5) :
                    if (iWelfareDcValue > 8000) :
                        iWelfareDcValue = 8000
                    print(f'차사위계층 : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 8,000')

            # 대가족 요금할인
            # A1 : 5인이상 가구,출산가구,3자녀이상 가구 (16,000원 한도)
            # A2 : 생명유지장치 (한도 없음)
            # 전기요금계((기본요금 ＋ 전력량요금 － 필수사용량 보장공제 ＋ 기후환경요금 ± 연료비조정액) － 200kWh이하감액) x 30% = 대가족 요금할인
            iBigFamValue = 0
            if (iBigFamBoolean) :
                iWelfareDcValue_temp = 0
                if (iWelfareDcBoolean >= 2) : # A2
                    iWelfareDcValue_temp = iWelfareDcValue
                iBigFamValue = math.floor((UsingCharge + adjustValue - elecBasic200Value - iWelfareDcValue_temp) * 0.3)
                if (iBigFamBoolean == 1) : # A1
                    if (iBigFamValue > 16000) :
                        iBigFamValue = 16000
                    print(f'대가족 요금할인 : {iBigFamValue} = 전기요금계({UsingCharge} + {adjustValue}) - {elecBasic200Value} - {iWelfareDcValue_temp} x30%, 최대 16000')
                else :
                    print(f'생명유지장치 : {iBigFamValue} = 전기요금계 - {elecBasic200Value} - {iWelfareDcValue_temp} x30%')

            # A B 중 큰 금액 적용
            # 차사위계층,기초생활은 중복할인 (A + B)
            if (iWelfareDcBoolean >= 3) : # 중복할인
                dcValue = iBigFamValue + iWelfareDcValue
                print(f'복지할인 {dcValue} = 대가족 요금할인 {iBigFamValue} + 복지 요금할인 {iWelfareDcValue}')
            else :
                if (iBigFamValue > iWelfareDcValue) :
                    dcValue = iBigFamValue
                else :
                    dcValue = iWelfareDcValue 
                print(f'복지할인 {dcValue} = 대가족 요금할인 {iBigFamValue} or 복지 요금할인 {iWelfareDcValue} 더큰것')

        print(f'최종 요금 : {round((UsingCharge + adjustValue - elecBasicValue - elecBasic200Value - dcValue) * 1.137)}원 = ((사용요금 {UsingCharge} + (조정액 {adjustValue}) - 필수사용량 보장공제{elecBasicValue} - 200kWh 이하 감액{elecBasic200Value} - 복지할인 {dcValue}) * 부가세,기금1.137)')
        totalCharge =  (UsingCharge + adjustValue - elecBasicValue - elecBasic200Value - dcValue) * 1.137

        if (totalCharge < 0) :
            totalCharge = 0
        elif (energy == 0) : # 사용량이 0 이면 50% 할인
            totalCharge = int(totalCharge/2)
        totalCharge =  math.floor(totalCharge/10)*10
        print(f'{totalCharge}')
        return totalCharge

kwh2won(k2w_config)