import pandas as pd

# 엑셀 파일 읽기
excel_file = '와석초_개선된QA_데이터_20250718_091247.xlsx'

try:
    # 모든 시트 읽기
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    print(f"엑셀 파일 '{excel_file}' 읽기 성공!")
    print(f"시트 개수: {len(excel_data)}")
    print()
    
    for sheet_name, df in excel_data.items():
        print(f"=== 시트: {sheet_name} ===")
        print(f"행 수: {len(df)}")
        print(f"열 수: {len(df.columns)}")
        print(f"열 이름: {list(df.columns)}")
        print()
        
        # 처음 3행 출력
        if len(df) > 0:
            print("처음 3행:")
            print(df.head(3))
            print()
        
        # 카테고리별 질문 수 확인
        if '카테고리' in df.columns:
            category_counts = df['카테고리'].value_counts()
            print("카테고리별 질문 수:")
            for category, count in category_counts.items():
                print(f"  {category}: {count}개")
            print()
        
        print("-" * 50)
        print()

except Exception as e:
    print(f"엑셀 파일 읽기 실패: {e}") 