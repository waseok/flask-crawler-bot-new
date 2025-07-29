import pandas as pd

excel_file = '와석초_개선된QA_데이터_20250718_091247.xlsx'

try:
    # 모든 시트 읽기
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    print(f"엑셀 파일 '{excel_file}' 읽기 성공!")
    print(f"시트 개수: {len(excel_data)}")
    
    for sheet_name, df in excel_data.items():
        print(f"\n=== 시트: {sheet_name} ===")
        print(f"행 수: {len(df)}")
        print(f"열 이름: {list(df.columns)}")
        
        # 처음 2행 출력
        if len(df) > 0:
            print("처음 2행:")
            print(df.head(2))
            print()
        
        print("-" * 50)

except Exception as e:
    print(f"오류 발생: {e}") 