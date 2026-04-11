# Pinny

시뮬레이터 위치를 빠르게 바꾸고 저장해두는 macOS용 CLI/TUI 도구입니다.
`xcrun simctl location`을 직접 외울 필요 없이, 자주 쓰는 좌표를 목록으로 관리하고 바로 적용할 수 있습니다.

## 이런 때 사용합니다

- 공항, 해외 도시처럼 테스트용 위치를 자주 바꿔야 할 때
- 여러 좌표를 저장해두고 번호만 골라서 바로 적용하고 싶을 때
- JSON 파일로 팀 공용 위치 목록을 가져오거나 덮어쓰고 싶을 때

## 할 수 있는 일

- `pinny`: 저장된 위치 목록 보기
- `pinny <number>`: 선택한 번호의 위치를 시뮬레이터에 즉시 적용
- `pinny 0`: 현재 Mac 위치를 가져와 시뮬레이터에 적용
- `pinny tui`: 위치 선택, 현재위치 적용, 추가, 삭제, 정렬을 화면에서 처리
- `pinny add <lat> <lon> <description>`: 위치 1개 추가
- `pinny add <list.json>`: JSON 파일에서 위치 목록 추가
- `pinny cover <list.json>`: JSON 파일 내용으로 전체 교체
- `pinny download`: 현재 위치 목록을 `locations.json`으로 저장
- `pinny --help`: 도움말 확인

저장 파일 기본 경로는 `~/.pinny/locations.json`입니다.
환경 변수 `PINNY_DATA_PATH`로 변경할 수 있습니다.
언어는 기본적으로 시스템 로케일을 따르며, `PINNY_LANG=ko|en`으로 강제할 수 있습니다.
목록이 비어 있는 상태로 TUI 실행 시 기본 위치 목록이 자동 추가됩니다.
`pinny 0`과 TUI의 현재위치 메뉴는 저장된 목록은 유지한 채, 현재 Mac 위치를 조회해 booted simulator에 적용합니다.
처음 실행 시 macOS 위치 권한 요청이 나타날 수 있으며, 위치 서비스가 꺼져 있거나 권한이 거부되면 적용에 실패할 수 있습니다.
실수로 권한을 거부했다면 시스템 설정 > 개인정보 보호 및 보안 > Location Services에서 `PinnyHostLocation`을 허용한 뒤 다시 실행하세요.
권한 팝업이 보이지 않거나 위치 조회 helper가 오래 대기하면 timeout 메시지를 출력하고 종료합니다. 이 경우 위치 권한 설정을 확인한 뒤 다시 실행하세요.

## 설치 (Homebrew)

```bash
brew tap venice81/pinny https://github.com/venice81/Pinny
brew install pinny
```

## 실행

```bash
pinny --help
pinny
pinny 0
pinny tui
```

## 빠른 예시

```bash
pinny add 37.5665 126.9780 "서울시청"
pinny add 35.6895 139.6917 "도쿄"
pinny
pinny 1
pinny 0
```

## JSON 형식

배열 루트 형식:

```json
[
  {"latitude": 37.5532, "longitude": 126.9837, "description": "서울역 주차장 입구"},
  {"latitude": 52.515854, "longitude": 13.407141, "description": "독일 에브라임 궁 박물관"}
]
```

또는 `locations` 키를 가진 객체와 축약 키도 지원합니다:

```json
{
  "locations": [
    {"lat": -62.222929, "lon": -58.786059, "desc": "남극 세종 과학기지"}
  ]
}
```

## 라이선스

MIT License
