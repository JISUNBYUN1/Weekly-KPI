# 적용 안내 · 20260916-r2

이 ZIP은 기존 프로젝트에 병합하는 업데이트 패키지입니다. 프로젝트 전체를 삭제하고 교체하는 패키지가 아닙니다.

## 적용 순서

1. ZIP을 풀고 코드 5개와 `reference_data` 폴더를 GitHub 저장소의 `streamlit_app.py`가 있는 위치에 한 번에 업로드합니다.
   - streamlit_app.py
   - executive_report.py
   - partner_views.py
   - report_data.py
   - dashboard_views.py
2. 기존 운영 데이터 파일은 그대로 둡니다. 이 패키지에는 운영 입력 JSON이 포함되어 있지 않습니다.
3. Streamlit Cloud의 **Manage app → Reboot app**을 실행합니다. Python이 이전에 읽은 모듈과 새 파일이 섞이지 않도록 합니다.
4. 사이드바에서 **버전 20260916-r2**를 확인합니다. 파일 버전이 다르면 앱이 안내문을 표시하고 실행을 중단합니다.
5. 스마트스토어 8월 W32, 프리미엄 8월 계, 품목별 8월 계 및 주차, 거래선 분석·기록 화면을 확인합니다.

운영 입력 파일(weekly_data, activity_overrides, feedback, manager_comments)은 배포 전 별도 백업을 권장합니다. 패키지는 이를 덮어쓰지 않지만 Streamlit 서버 로컬 파일의 재배포 후 영구 보존까지 보장하지는 않습니다.

## 기준 데이터

`reference_data`는 앞서 첨부받은 기준 데이터의 읽기 전용 복구 자료입니다. 정상 운영 파일이 있으면 그 파일을 우선하며, 파일이 없거나 읽을 수 없을 때 사용합니다. 최신 실적이라고 임의로 표시하지 않습니다. 신규 입력과 활동 수정·삭제는 기준 데이터보다 우선합니다.

- STAR 2025: 별도 첨부 원본과 26,553행 및 매출·실판매 합계 일치.
- STAR 2026: 별도 첨부 원본과 25,512행 및 매출·실판매 합계 일치.
- 기존 활동: 241건.
- 구매비중 복원: `(취합본) PP3G_주차별KPI현황_W36주.xlsx`의 `③ SOP_스토어_고객변화` 시트에서 17개 주차, 113개 거래선·주차별 기록. 출처 행·열은 `purchase_provenance.json`에 기록.
- 구매비중은 신규 구매자 ÷ (신규 구매자 + 재구매자), 재구매 비중은 그 반대. 월간 값을 주간 값으로 복사하지 않음.

## 검증 범위

자동 테스트 71건 통과(기존 및 데이터 연결 61건 + 실패 조건 중심 10건). Python 문법 검사 통과.
이 환경에서는 Streamlit 설치가 불가능해 실제 브라우저 실행 및 Python 3.14 운영 환경 검증은 수행하지 못했습니다. GitHub/운영 서버에 직접 배포하지 않았습니다.

테스트 실행: `PYTHONPATH=. python -m unittest discover -s tests -q` 및 `python -m unittest test_executive -q`.
