"""Constants for the Detailed Hello World Push integration."""

# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN = "kwh_to_won"
VERSION = "0.0.1"
MODEL = "kwh2won"
MANUFACTURER = ""


PRESSURE_OPTION = {
    'low': '가정용 저압',
    'high': '가정용 고압'
}
BIGFAM_DC_OPTION = {
    0:'해당없음',
    1:'5인이상 가구,출산가구,3자녀이상 가구',
    2:'생명유지장치'
}
WELFARE_DC_OPTION = {
    0:'해당없음',
    1:'독립유공자,국가유공자,5.18민주유공자,장애인',
    2:'사회복지시설',
    3:'기초생활(생계.의료)',
    4:'기초생활(주거.교육)',
    5:'차사위계층'
}

CALC_PARAMETER = {
    'low': {
        'basicprice' : [910, 1600, 7300], # 기본요금(원/호)
        'kwhprice' : [88.3, 182.9, 275.6], # 전력량 요금(원/kWh)
        # 'kwhprice' : [93.3, 187.9, 280.6], # 전력량 요금(원/kWh) - 개편전 요금
        'kwhsectionUp' : [0, 200, 400], # 구간(kWh - 상계)
        'kwhsectionDown' : [0, 300, 450], # 구간(kWh - 하계)(7~8월)
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        # 'adjustment' : [-5, 5.3, -3], # 환경비용차감 + 기후환경요금 + 연료비조정액 - 개편전 요금
        'elecBasicLimit' : 2000,
        'elecBasic200Limit' : 4000
    },
    'high': {
        'basicprice' : [910, 1600, 7300], # 기본요금(원/호)
        'kwhprice' : [88.3, 182.9, 275.6], # 전력량 요금(원/kWh)
        'kwhsectionUp' : [0, 200, 400], # 구간(kWh - 상계)
        'kwhsectionDown' : [0, 300, 450], # 구간(kWh - 하계)(7~8월)
        'adjustment' : [-5, 5.3, 0], # 환경비용차감 + 기후환경요금 + 연료비조정액
        'elecBasicLimit' : 1500,
        'elecBasic200Limit' : 2500
    },
}