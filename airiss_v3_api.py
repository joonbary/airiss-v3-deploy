# airiss_v3_api.py
# AIRISS v3.0 웹 서버 API 코드

import os
import io
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd
import uvicorn

# ⭐ 여러분이 만든 Core Framework 가져오기
# 실제로는 이 부분을 Gist 코드로 대체해야 합니다
# from airiss_v3_core import AIRISS_FRAMEWORK, AIRISSHybridAnalyzer, hybrid_analyzer

# 🌟 웹 서버 시작하기
app = FastAPI(
    title="AIRISS v3.0 - OK금융그룹 AI 인재분석 시스템",
    description="직원 평가를 AI로 분석하는 시스템",
    version="3.0.0"
)

# 📦 데이터 보관소 (분석 결과 임시 저장)
class DataStore:
    def __init__(self):
        self.files = {}      # 업로드된 파일들
        self.jobs = {}       # 분석 작업들
        self.results = {}    # 분석 결과들
    
    def add_file(self, file_id: str, data: Dict):
        """파일 정보 저장"""
        self.files[file_id] = data
    
    def get_file(self, file_id: str) -> Optional[Dict]:
        """파일 정보 가져오기"""
        return self.files.get(file_id)
    
    def add_job(self, job_id: str, data: Dict):
        """분석 작업 저장"""
        self.jobs[job_id] = data
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """분석 작업 가져오기"""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, updates: Dict):
        """분석 작업 업데이트"""
        if job_id in self.jobs:
            self.jobs[job_id].update(updates)

# 보관소 만들기
store = DataStore()

# 📋 분석 요청 양식
class AnalysisRequest(BaseModel):
    file_id: str                              # 어떤 파일?
    sample_size: int = 25                     # 몇 명 분석?
    analysis_mode: str = "hybrid"             # 분석 방식
    openai_api_key: Optional[str] = None     # AI 피드백 사용?
    enable_ai_feedback: bool = False          # AI 피드백 켜기/끄기

# 🏠 메인 페이지
@app.get("/")
async def main_page():
    return {"message": "AIRISS v3.0 시스템에 오신 것을 환영합니다!"}

# 📤 파일 업로드 API
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Excel이나 CSV 파일을 업로드하는 기능"""
    
    try:
        # 1. 파일 이름 확인
        print(f"📁 파일 업로드 시작: {file.filename}")
        
        # 2. 파일 읽기
        contents = await file.read()
        
        # 3. Excel인지 CSV인지 확인하고 읽기
        if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
            # Excel 파일 읽기
            df = pd.read_excel(io.BytesIO(contents))
            print("✅ Excel 파일 읽기 성공!")
        elif file.filename.endswith('.csv'):
            # CSV 파일 읽기
            df = pd.read_csv(io.BytesIO(contents))
            print("✅ CSV 파일 읽기 성공!")
        else:
            return {"error": "Excel(.xlsx, .xls) 또는 CSV 파일만 가능해요!"}
        
        # 4. 파일 ID 만들기 (고유한 이름)
        file_id = str(uuid.uuid4())
        
        # 5. 데이터 정보 확인
        total_records = len(df)  # 총 몇 명?
        columns = list(df.columns)  # 어떤 항목들?
        
        # 6. 평가 의견 컬럼 찾기
        opinion_columns = []
        for col in columns:
            if any(word in col.lower() for word in ['의견', 'opinion', '평가', 'feedback']):
                opinion_columns.append(col)
        
        # 7. 보관소에 저장
        store.add_file(file_id, {
            'dataframe': df,
            'filename': file.filename,
            'upload_time': datetime.now(),
            'total_records': total_records,
            'columns': columns,
            'opinion_columns': opinion_columns
        })
        
        # 8. 결과 알려주기
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "total_records": total_records,
            "columns_found": len(columns),
            "opinion_columns": opinion_columns,
            "message": f"✅ {total_records}명의 데이터를 찾았어요!"
        }
        
    except Exception as e:
        return {"error": f"파일 처리 중 오류: {str(e)}"}

# 🚀 분석 시작 API
@app.post("/analyze")
async def start_analysis(request: AnalysisRequest):
    """업로드된 파일을 분석 시작"""
    
    # 1. 파일 찾기
    file_data = store.get_file(request.file_id)
    if not file_data:
        return {"error": "파일을 찾을 수 없어요!"}
    
    # 2. 작업 ID 만들기
    job_id = str(uuid.uuid4())
    
    # 3. 작업 정보 저장
    store.add_job(job_id, {
        "status": "processing",  # 처리 중
        "file_id": request.file_id,
        "sample_size": request.sample_size,
        "start_time": datetime.now(),
        "total": request.sample_size,
        "processed": 0,
        "results": []
    })
    
    # 4. 백그라운드에서 분석 시작
    # (실제로는 여기서 Core Framework의 분석기를 사용합니다)
    # asyncio.create_task(process_analysis(job_id))
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "분석을 시작했어요! 잠시만 기다려주세요."
    }

# 📊 분석 상태 확인 API
@app.get("/status/{job_id}")
async def check_status(job_id: str):
    """분석이 얼마나 진행됐는지 확인"""
    
    job_data = store.get_job(job_id)
    if not job_data:
        return {"error": "작업을 찾을 수 없어요!"}
    
    # 진행률 계산
    progress = 0
    if job_data["total"] > 0:
        progress = (job_data["processed"] / job_data["total"]) * 100
    
    return {
        "status": job_data["status"],
        "progress": round(progress, 1),
        "processed": job_data["processed"],
        "total": job_data["total"],
        "message": f"{job_data['processed']}/{job_data['total']}명 분석 완료"
    }

# 💾 결과 다운로드 API
@app.get("/download/{job_id}")
async def download_results(job_id: str):
    """분석 결과 Excel 파일로 다운로드"""
    
    job_data = store.get_job(job_id)
    if not job_data:
        return {"error": "작업을 찾을 수 없어요!"}
    
    if job_data["status"] != "completed":
        return {"error": "아직 분석이 끝나지 않았어요!"}
    
    # 실제로는 여기서 Excel 파일을 만들어서 전송
    return {
        "message": "다운로드 준비 완료!",
        "filename": "AIRISS_분석결과.xlsx"
    }

# 🏥 시스템 상태 확인
@app.get("/health")
async def health_check():
    """시스템이 정상인지 확인"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "message": "AIRISS 시스템 정상 작동 중!"
    }

# 서버 실행 코드 (나중에 사용)
if __name__ == "__main__":
    print("🚀 AIRISS v3.0 서버 시작!")
    print("🌐 http://localhost:8000 에서 확인하세요")
    # uvicorn.run(app, host="127.0.0.1", port=8000)