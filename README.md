# 전기요금계산 센서 for HA

## 주요기능
- 전기요금 계산 센서
  - 전기 사용량을 사용요금으로 계산
  - 가정용저압, 고압 지원
  - 대가족할인 및 복지할인 계산 지원
  - 하계요금 지원
  - 슈퍼유저요금 지원
- 예상사용량 센서
- 예상사용요금 센서

<br>

## 한전 전기요금 자료 링크
- [한전 전기요금계산기](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/J/A/CYJAPP000NFL.jsp)
- [전기요금표](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/E/E/CYEEHP00101.jsp)
- [복지할인요금제](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/H/C/CYHCHP00208.jsp), [대가족,생명유지장치요금제](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/H/C/CYHCHP00209.jsp)
- [연료비조정금액](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/H/C/CYHCHP00210.jsp), [기후환경요금](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/H/C/CYHCHP00211.jsp)

<br>

## 스크린샷
![screen1-1.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-1.jpg)<br>
![screen1-0.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-0.jpg)
![screen1-2.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-2.jpg)
![screen1-3.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-3.jpg)
![screen1-4.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-4.jpg)

<br>

## 판올림
| Version | Date        | 내용              |
| :-----: | :---------: | ----------------------- |
| v0.0.1  | 2021.12.13  | 템플릿센서 통합구서요소로 변경 |
| v0.0.2  | 2021.12.14  | 할인 설정 지원 |
| v0.0.3  | 2021.12.15  | 고압지원 |
| v0.0.4  | 2021.12.16  | 오타수정 |
| v0.0.5  | 2021.12.16  | 200kwh 이하 할인 금액 변수 누락 수정 |
| v0.0.6  | 2021.12.18  | 구성옵션 추가 (재시작시반영), 마그레이션 버전을 고정 |
| v1.0.0  | 2021.12.20  | 계산식 수정, 슈퍼사용자요금 추가, 복지할인 하계 구분 |
| v1.1.0  | 2021.12.21  | 검침일을 검침시작일로, 센서의 속성지정 |
| v1.1.1  | 2021.12.22  | 월이 바뀌었을때 월길이 계산 오류 수정 |
| v1.1.3  | 2021.12.25  | 센서 입력에서 센서 선택으로 수정, entitiy_id 접미사 변경으로 마그래이션 불가 (지우고, 다시 등록필요) |
| v1.1.4  | 2021.12.25  | 검침일 선택형으로 수정, 누진계산 오류 수정, 예상 사용량 일수 계산 오류 수정 |
| v1.1.5  | 2021.12.27  | 전력량단가를 환경비용요금 적용전단가(계정전단가)로 수정 (af950833님의 제보) |
| v1.1.6  | 2021.12.27  | 누진 계산 오류 수정 |


<br>

## 설치
- 수동설치 또는 HACS를 이용해 설치를 할수 있습니다.
### 수동
- HA 설치 경로 아래 custom_components에 kwh_to_won폴더 안의 전체 파일을 복사해줍니다.<br>
  `<config directory>/custom_components/kwh_to_won/`<br>
- Home-Assistant 를 재시작합니다<br>
### HACS
- HACS > Integretions > 우측상단 메뉴 > Custom repositories 선택
- `https://github.com/dugurs/kwh_to_won` 주소 입력, Category에 'integration' 선택 후, 저장
- HACS > Integretions 메뉴 선택 후, `kwh_to_won` 혹은 `전기요금 계산 센서` 검색하여 설치

<br>

## 사용
### 월간 누적 사용량 센서
- 검침일에 맞줘 카운팅되는 월간 누적 사용량 센서가 있어야 합니다.
- 없다면 아래와같이 [`utility_meter`](https://www.home-assistant.io/integrations/utility_meter/)를 이용해 만들어줘야 합니다.
```
utility_meter:
  pzemac_energy_monthly:
    source: sensor.pzemac_energy
    cycle: monthly
    offset:
      days: 11
```
### 통합구성요소 추가
- 구성 > 통합구성요소 > 통합구성요소 추가하기 > 전기요금 계산 센서 > 필수요소를 모두 입력후, 확인.
- 월간 전기 사용량 센서는 다음과 같은 속성이어야 합니다.
  - `device_class: energy`, `state_class: total_increasing`, `unit_of_measurement: kWh`

### 생성되는 센서
- 통합구성요소 추가시 이름을 `test`로 했다면 다음과 같은 3개의 센서가 생성됩니다.
  - `sensor.test_kwhto_won` 전기요금 센서
  - `sensor.test_kwhto_forecast` 예상 사용량 센서
  - `sensor.test_kwhto_forecast_won` 예상 전기요금 센서

<br>

## 보완 예정 사항

<br>

## 발견된 문제점
- 생성된 센서값이 업데이트 되지 전까지 '알수없음'
