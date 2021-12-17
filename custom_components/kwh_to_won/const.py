"""Constants for the Detailed Hello World Push integration."""

# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN = "kwh_to_won"
MODEL = "kwh2won"
MANUFACTURER = "전기요금센서"


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
