# Pinny

`xcrun simctl location`을 쉽게 쓰기 위한 Python TUI/CLI 도구입니다.

## 기능

- `pinny` : TUI 실행 (위치지정/추가/삭제/정렬/종료)
- `pinny add <lat> <lon> <description>` : 단건 추가
- `pinny add <list.json>` : 목록 추가 (중복 좌표 자동 생략)
- `pinny cover <list.json>` : 목록으로 전체 덮어쓰기
- `pinny download` : 전체 목록 JSON 출력
- `pinny --help` : 도움말

저장 파일 기본 경로는 `~/.pinny/locations.json`입니다.
환경 변수 `PINNY_DATA_PATH`로 변경할 수 있습니다.
언어는 기본적으로 시스템 로케일을 따르며, `PINNY_LANG=ko|en`으로 강제할 수 있습니다.
목록이 비어 있는 상태로 TUI 실행 시 기본 위치 목록이 자동 추가됩니다.

## 설치/실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pinny --help
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

## Homebrew 배포

`Formula/pinny.rb`를 Tap 저장소에 두고 배포할 수 있습니다.

1. GitHub 릴리즈 태그 생성 (`v0.1.0` 등)
2. 소스 tarball sha256 계산
3. `Formula/pinny.rb`의 `url`, `sha256` 값 갱신
4. `brew tap <you>/<tap>` 후 `brew install pinny`
