# YouTube 보행자 안전 영상 크롤러

보행자 안전 및 위험 상황과 관련된 YouTube 영상을 수집하는 툴입니다. 수집된 영상은 연구 목적으로만 사용하시길 권장드립니다.

## 주요 기능

- **YouTube API**: 공식 YouTube Data API를 사용하여 효율적이고 규정을 준수하는 검색 수행
- **yt-dlp 사용**: yt-dlp 라이브러리를 활용하여 YouTube의 다운로드 제한 극복
- **다중 대체 방법**: 높은 성공률을 보장하기 위한 여러 다운로드 접근 방식 구현
- **맞춤형 검색**: 사용자 지정 검색어 및 영상 필터링 옵션 추가 가능
- **메타데이터 기록**: 다운로드된 각 영상에 대한 상세 정보 저장
- **예외 처리 구현**: 다양한 오류 상황을 처리하기 위한 재시도 및 대체 메커니즘 구현

## 설치 방법

1. 필요한 Python 패키지 설치:

```powershell
pip install -r requirements.txt
```

2. 요구 사항:
   - Python 3.6 이상
   - [Google Cloud Console](https://console.cloud.google.com/)에서 발급받은 YouTube Data API v3 키
   - yt-dlp (requirements.txt를 통해 자동 설치)

## 사용 방법

다음 명령어로 크롤러를 실행합니다:

```powershell
python YoutubeCrawler.py --api-key 발급받은_API_키 --max-videos 10 --min-duration 10 --max-duration 180
```

위 명령으로 메인 파일을 실행시키면 전달한 옵션에 따라 영상을 검색하고 다운로드를 시작합니다.

## 명령줄 인수

크롤러는 다양한 명령줄 옵션을 통해 동작을 사용자 정의할 수 있습니다:

- `--api-key`: YouTube Data API 키 (필수)
- `--output` 또는 `-o`: 다운로드된 영상을 저장할 디렉토리 (기본값: "./downloaded_videos")
- `--max-videos` 또는 `-m`: 다운로드할 최대 영상 수 (기본값: 50)
- `--min-duration`: 최소 영상 길이(초) (기본값: 5)
- `--max-duration`: 최대 영상 길이(초) (기본값: 300)
- `--search-terms` 또는 `-s`: 사용자 정의 검색어 (공백으로 구분)

사용자 정의 검색어 예시:

```powershell
python YoutubeCrawler.py --api-key 발급받은_API_키 --max-videos 5 --search-terms "보행자 사고 영상" "횡단보도 위험"
```

## 작동 원리

크롤러가 다음과 알고리즘으로 YouTube 다운로드 제약에 대해 대처하도록 했습니다:

1. **yt-dlp 우선 사용**: YouTube 제한을 우회하는 해결책을 지속적으로 유지하는 강력한 yt-dlp 라이브러리 사용
2. **URL 추출 알고리즘으로 전환**: yt-dlp에 문제가 발생할 경우 직접 URL 추출 방법으로 대체
3. **재시도 메커니즘**: 다운로드 실패 시 지수적 백오프를 통한 재시도 구현

위 알고리즘으로 다음과 같은 문제를 해결했습니다:
- PyTube와 같은 라이브러리의 빈번한 HTTP 400/403 오류 발생
- Selenium과 같은 리소스 집약적인 브라우저 자동화 없이도 가능

## 기본 검색어

크롤러는 기본적으로 다음 검색어를 사용하여 영상을 검색합니다:
- pedestrian near miss video
- pedestrian accident footage
- pedestrian crossing danger cctv
- pedestrian safety violation video
- pedestrian hazard dashcam
- pedestrian traffic incident footage
- pedestrian close call video
- pedestrian intersection danger
- road safety pedestrian accident
- crosswalk safety violation

## 출력 결과

크롤러는 세 개의 파일을 생성합니다:

1. **다운로드된 영상**: 모든 영상은 지정된 출력 디렉토리에 영상 ID와 제목을 포함한 파일명으로 저장됩니다.

2. **메타데이터 CSV**: "video_metadata.csv"라는 CSV 파일이 출력 디렉토리에 생성되며 다음과 같은 다운로드된 각 영상의 메타데이터를 포함합니다:
   - 영상 ID 및 제목
   - URL 및 채널 이름
   - 길이 및 조회수
   - 게시 날짜
   - 영상을 찾는 데 사용된 검색어

3. **로그 파일**: "youtube_crawler_log.txt" 파일은 프로그램 실행 과정 동안 발생한 터미널 출력으로, 오류 발생 시 참고할 수 있도록 했습니다.

## YouTube Data API 키 얻기

이 크롤러를 사용하려면 YouTube Data API v3 키가 필요합니다:

1. [Google Cloud Console](https://console.cloud.google.com/)로 이동
2. 새 프로젝트 생성
3. YouTube Data API v3 활성화
4. 사용자 인증 정보 생성 (API 키)
5. `YoutubeCrawler.py` 스크립트에서 API 키 사용

## 문제 해결

문제가 발생할 경우:

1. **API 제한 확인**: YouTube Data API에는 일일 할당량이 있으므로 초과하지 않았는지 확인
2. **네트워크 문제**: 인터넷 연결을 확인하고 지역 제한이 있는 경우 VPN 사용 고려
3. **yt-dlp 업데이트**: YouTube는 시스템을 자주 변경하므로 `pip install -U yt-dlp` 명령으로 최신 버전을 유지
4. **속도 제한**: 코드의 임의 지연 값을 수정하여 요청 사이에 더 긴 지연 추가
5. **권한**: 스크립트가 출력 디렉토리에 쓰기 권한이 있는지 확인
