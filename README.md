# 전기요금계산 센서 (가정용) for HomeAssistant

## 주요기능
- 전기요금 계산 센서 및 서비스
  - 전기 사용량을 사용요금으로 계산
  - 가정용저압, 고압 지원
  - 대가족할인 및 복지할인 계산 지원
  - 하계요금 지원
  - 슈퍼유저요금 지원
- 예상사용량 센서
- 예상사용요금 센서
- 현재 누진단계 센서 (1단계, 2단계, 3단계)
- 한전 요금표(`rates.json`) 자동/수동 갱신 시스템 (GitHub 원격 동기화 및 HA 재시작 없는 즉시 반영)

<br>

## 한전 전기요금 자료 링크
- [전기요금계산기](https://online.kepco.co.kr/PRM033D00)
- [전기요금표](https://online.kepco.co.kr/PRM004D00)
- [전기요금제제도](https://online.kepco.co.kr/PRM088D00)

<br>

## 스크린샷
![kwh2won](https://user-images.githubusercontent.com/41262994/187405383-2b369903-6a5e-4ed8-9eae-e1ab71b434ab.jpg)<br>
![screen1-0.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-0.jpg)
![screen1-2.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-2.jpg)
![screen1-3.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-3.jpg)
![screen1-4.jpg](https://dugurs.github.io/kwh_to_won/images/screen1-4.jpg)


<br>

## 설치
- 수동설치 또는 HACS를 이용해 설치를 할수 있습니다.
### 수동
- HA 설치 경로 아래 custom_components에 kwh_to_won폴더 안의 전체 파일을 복사해줍니다.<br>
  `<config directory>/custom_components/kwh_to_won/`<br>
- Home-Assistant 를 재시작합니다<br>
### HACS
- [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=kwh_to_won&owner=dugurs&category=integration)
  - HACS > Integretions > 우측상단 메뉴 > Custom repositories 선택
    - `https://github.com/dugurs/kwh_to_won` 주소 입력, Category에 'integration' 선택 후, 저장
  - HACS > Integretions 메뉴 선택 후, `kwh_to_won` 검색하여 설치

<br>

## 사용

### 통합구성요소 추가
- [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kwh_to_won)
  - 설정 > 기기및서비스 > 통합구성요소 추가하기 > `kwh_to_won` 검색하여 추가
- 월간 전기 사용량 센서는 다음과 같은 속성이어야 합니다.
  - `unit_of_measurement: kWh`, `device_class: energy`, `state_class: total_increasing, total`
- ~~전월 전기 사용량 센서는 다음과 같은 속성이어야 합니다.~~
  - ~~`unit_of_measurement: kWh`, `device_class: energy`, `state_class: total`~~
- ~~예상 전기 사용량 센서는 다음과 같은 속성이어야 합니다.~~
  - ~~`unit_of_measurement: kWh`, `device_class: energy`, `state_class: total`~~
### 생성되는 센서
- 통합구성요소 추가 시 이름을 `test`로 했다면 다음과 같은 4개의 센서가 기본 생성됩니다.
  - `sensor.test_kwhto_won` 전기요금 센서
  - `sensor.test_kwhto_forecast` 예상 사용량 센서
  - `sensor.test_kwhto_forecast_won` 예상 전기요금 센서
  - `sensor.test_kwhto_step` 현재 누진단계 센서 (1단계, 2단계, 3단계)
- 전월 사용량, 전전월 사용량 센서를 입력 했다면 다음과 같은 센서가 추가로 생성 됩니다.
  - `sensor.test_kwhto_won_prev` 전월 전기요금 센서
  - `sensor.test_kwhto_won_prev2` 전전월 전기요금 센서
- 보정계수를 0보다 크게 설정하면 다음과 같은 1개의 센서가 추가로 생성 됩니다.
  - `sensor.test_kwhto_kwh` 전기사용량 센서
  - 보정계수 = 실제(검침)사용량 / 측정(센서)사용량

## 제공 액션 (서비스)

### 1. 전기요금 계산 (`kwh_to_won.calculate`)
21년 1월 이후 (21년 2월분 요금) 부터 계산이 가능합니다.<br>
오토메이션이나 스크립트에서 계산값을 응답 데이터(Response Data)로 반환받아 활용할 수 있습니다.
```yaml
action: kwh_to_won.calculate
data:
  checkDay: 11
  kwh: 410
  today: "2025-02-15"
  pressure: low
  bigfamDcCfg: 1
  welfareDcCfg: 1
```

### 2. 요금표 즉시 재로드 (`kwh_to_won.reload_rates`)
Home Assistant 재시작 없이 로컬 `rates.json` 파일을 즉시 다시 읽어 등록된 모든 센서에 실시간 반영합니다.
```yaml
action: kwh_to_won.reload_rates
```

### 3. 최신 요금표 원격 갱신 (`kwh_to_won.update_rates`)
공식 GitHub 저장소에서 최신 요금표(`rates.json`)를 다운로드하고 유효성을 검증한 뒤 로컬 파일을 갱신합니다.<br>
(기본적으로 매일 새벽 04:00 및 HA 시작 시 자동 확인되며, 요금표 변경 시 영구 알림이 등록됩니다.)
```yaml
action: kwh_to_won.update_rates
data:
  force: false  # true 설정 시 버전이 동일해도 강제 재다운로드
```

<br>

### 월간 누적 사용량 센서 및 전월 사용량 센서
- 검침일에 맞줘 카운팅되는 월간 누적 사용량 센서가 있어야 합니다.
- 없다면 아래와같이 [`utility_meter`](https://www.home-assistant.io/integrations/utility_meter/)를 이용해 만들어줘야 합니다.

```

# 매달 11일 0시 0분에 리셋 (검침 시작일 11일)
utility_meter:
  xxxx_energy_monthly:
    source: sensor.xxxx_energy
    cycle: monthly
    offset:
      days: 10
      
```
<br>

- 전월 사용량 센서는 다음과 같이 만들수 있습니다. [`template`](https://www.home-assistant.io/integrations/template/) <br>
```
template:
  - sensor:
      - name: "xxxx_energy_prev_monthly"
        unique_id: xxxx_energy_prev_monthly
        state: "{{ state_attr('sensor.xxxx_energy_monthly','last_period') |round(1) }}"
        unit_of_measurement: kWh
        device_class: energy
        attributes:
          state_class: total
```
<br>

- 전전월 사용량 센서는 전월 사용량 센서를 이용해 다름과 같이 만들수 있습니다. 
```
template:
  - sensor:
    - trigger:
        - platform: state
          entity_id: sensor.xxxx_energy_prev_monthly
      sensor:
        - name: xxxx_energy_prev2_monthly
          unique_id: "xxxx_energy_prev2_monthly"
          unit_of_measurement: kWh
          state: "{{ trigger.from_state.state }}"
          device_class: energy
          attributes:
            state_class: total
```
또는 (아래 자동화로 만드를 것을 추천)
```
input_number:
  xxxx_energy_prev2_monthly:
    name: "전기 전전월 사용량"
    unit_of_measurement: "kWh"
    icon: mdi:conuter
    min: 0
    max: 9999
    step: 0.01
    mode: box

automation:
  - id: '1713958xxxxxx'
    alias: xxxx_energy_prev2_monthly
    description: '전기 전전월 사용량'
    trigger:
    - platform: state
      entity_id:
      - sensor.xxxx_energy_prev_monthly
    condition:
    - condition: template
      value_template: '{{ trigger.to_state.state|float(0) > 0 and trigger.from_state.state|float(0) > 0 }}'
    action:
    - service: input_number.set_value
      data:
        value: '{{ trigger.from_state.state }}'
      target:
        entity_id: input_number.xxxx_energy_prev2_monthly
    mode: single
```
<br>

- Wh단위를 kWh로 변경하는 방법.<br>
```
template:
  sensor:
    - name: pmm_this_month_energy_kwh
      unique_id: "pmm_this_month_energy_kwh"
      state: "{{ states('sensor.pmm_xx_xx_xx_xx_xx_this_month_energy')|float / 1000 }}"
      unit_of_measurement: kWh
      device_class: energy
      attributes:
        state_class: total_increasing
        last_reset: "{{ state_attr('sensor.pmm_xx_xx_xx_xx_xx_this_month_energy','last_reset') }}"
```


## 보완 예정 사항
- 
<br>

## 발견된 문제점
- 전월 전기요금 센서 생성 후 사용안한으로 변경시 자동제거 안됨(수동삭제 가능)
<br>


<br>

## 변경 내역 (Changelog)
버전별 상세 변경 내역은 [CHANGELOG.md](CHANGELOG.md)를 참고하세요.



## 도움
- https://github.com/oukene/extend_temperature <br>
  위 통합구성요소를 기반으로 작성되었습니다.
- https://developers.home-assistant.io/docs/creating_component_index
- https://github.com/home-assistant/core/tree/dev/homeassistant/helpers
