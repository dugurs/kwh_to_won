![HACS][hacs-shield]
![Version v0.0.4][version-shield]

# kwh2won
전기요금 계산기
- 전기 사용량을 사용요금으로 계산
- 가정용저압, 고압 지원
- 대가족할인 및 복지할인 계산 지원

한전 전기요금 계산기 (개편전 단가임!!)
- (https://cyber.kepco.co.kr/ckepco/front/jsp/CY/J/A/CYJAPP000NFL.jsp)

## 스크린샷
![screen1-1.jpg](https://raw.githubusercontent.com/dugurs/kwh_to_won/main/images/screen1-1.jpg)
![screen1-2.jpg](https://raw.githubusercontent.com/dugurs/kwh_to_won/main/images/screen1-2.jpg)
![screen1-3.jpg](https://raw.githubusercontent.com/dugurs/kwh_to_won/main/images/screen1-3.jpg)
![screen1-4.jpg](https://raw.githubusercontent.com/dugurs/kwh_to_won/main/images/screen1-4.jpg)


<br>

## Version history
| Version | Date        | 내용              |
| :-----: | :---------: | ----------------------- |
| v0.0.1  | 2021.12.13  | 템플릿센서 통합구서요소로 변경 |
| v0.0.2  | 2021.12.14  | 할인 설정 지원 |
| v0.0.3  | 2021.12.15  | 고압지원 |
| v0.0.4  | 2021.12.16  | 오타수정 |


<br>

## 설치
### Manual
- HA 설치 경로 아래 custom_components에 kwh_to_won폴더 안의 전체 파일을 복사해줍니다.<br>
  `<config directory>/custom_components/kwh_to_won/`<br>
- configuration.yaml 파일에 설정을 추가합니다.<br>
- Home-Assistant 를 재시작합니다<br>
### HACS
- HACS > Integretions > 우측상단 메뉴 > Custom repositories 선택
- 'https://github.com/dugurs/kwh_to_won' 주소 입력, Category에 'integration' 선택 후, 저장
- HACS > Integretions 메뉴 선택 후, kwh_to_won 검색하여 설치

<br>

## 보완 사항
- 

<br>

## 발견된 문제점
- 생성된 센서값이 업데이트 되지 전까지 '알수없음'
