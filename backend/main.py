from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import io
import os
from . import grading_utils
from typing import Dict, List

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with DB or file storage for production)
# For simplicity, we save current dataframe to disk
# Use absolute paths relative to this script to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "current_data.xlsx")
RESULT_FILE = os.path.join(BASE_DIR, "result_data.xlsx")
COCKPIT_FILE = os.path.join(BASE_DIR, "cockpit_data.xlsx")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        # Validate Excel
        df = pd.read_excel(io.BytesIO(content))
        # Save locally
        df.to_excel(DATA_FILE, index=False)
        return {"message": "Upload successful", "rows": len(df), "columns": df.columns.tolist()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auto-grade")
async def auto_grade():
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        df = pd.read_excel(DATA_FILE)
        df_calc = grading_utils.calculate_metrics(df)
        best_df, metrics = grading_utils.optimize_grading(df_calc)
        
        # Save result
        best_df.to_excel(RESULT_FILE, index=False)
        
        # Generate summary
        summary_df = grading_utils.generate_summary(best_df)
        district_stats = grading_utils.generate_district_summary(best_df)
        district_detail = grading_utils.generate_district_grade_detail(best_df)
        
        return {
            "metrics": metrics,
            "summary": summary_df.to_dict(orient="records"),
            "district_stats": district_stats,
            "district_detail": district_detail,
            "top50": best_df.head(50).fillna("").to_dict(orient="records")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class ManualGradeRequest(BaseModel):
    thresholds: Dict[int, float]

@app.post("/api/manual-grade")
async def manual_grade(request: ManualGradeRequest):
    if not os.path.exists(RESULT_FILE):
        # Fallback to DATA_FILE if exists and run calc
        if os.path.exists(DATA_FILE):
            df = pd.read_excel(DATA_FILE)
            df = grading_utils.calculate_metrics(df)
        else:
            raise HTTPException(status_code=400, detail="No data available")
    else:
        # Load existing result to keep other columns
        df = pd.read_excel(RESULT_FILE)
    
    try:
        # Re-assign based on thresholds
        # Note: We need '总分' which should be in df if loaded from RESULT_FILE or calculated
        if '总分' not in df.columns:
             df = grading_utils.calculate_metrics(df)
             
        new_df = grading_utils.assign_grades_by_thresholds(df, request.thresholds)
        
        # Save new result
        new_df.to_excel(RESULT_FILE, index=False)
        
        summary_df = grading_utils.generate_summary(new_df)
        district_stats = grading_utils.generate_district_summary(new_df)
        district_detail = grading_utils.generate_district_grade_detail(new_df)
        
        return {
            "summary": summary_df.to_dict(orient="records"),
            "district_stats": district_stats,
            "district_detail": district_detail,
            "top50": new_df.head(50).fillna("").to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preview-manual-grade")
async def preview_manual_grade(request: ManualGradeRequest):
    """
    Preview grading results without saving to file.
    Used for real-time updates in frontend.
    """
    if not os.path.exists(RESULT_FILE) and not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=400, detail="No data available")
        
    try:
        if os.path.exists(RESULT_FILE):
            df = pd.read_excel(RESULT_FILE)
        else:
            df = pd.read_excel(DATA_FILE)
            
        if '总分' not in df.columns:
             df = grading_utils.calculate_metrics(df)
             
        new_df = grading_utils.assign_grades_by_thresholds(df, request.thresholds)
        summary_df = grading_utils.generate_summary(new_df)
        district_stats = grading_utils.generate_district_summary(new_df)
        district_detail = grading_utils.generate_district_grade_detail(new_df)
        
        return {
            "summary": summary_df.to_dict(orient="records"),
            "district_stats": district_stats,
            "district_detail": district_detail
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download")
async def download_result():
    if not os.path.exists(RESULT_FILE):
        # If no result file, check if we have data to generate it on the fly
        if os.path.exists(DATA_FILE):
            # Try to run a quick calc to generate it? 
            # Or just return error. Better to return error if user hasn't run grading.
            pass
        raise HTTPException(status_code=400, detail="No result generated. Please run auto-grading first.")
    
    try:
        # Create a clean excel with Summary and Detail
        df = pd.read_excel(RESULT_FILE)
        
        # Use the new export function
        # Calculate metrics for rule validation display
        # We need to re-run metrics calculation or save metrics during auto-grade
        # For now, let's re-run optimization *just* to get metrics if possible, or 
        # better yet, modify generate_export_data to calc metrics internally if not provided.
        # It already does some calc internally.
        
        # We need to pass metrics if we want strict rule reporting (like failed districts list)
        # But we didn't save metrics to a file. 
        # Let's rely on internal recalculation in generate_export_data for now.
        # It handles missing metrics gracefully.
        
        detail_df, summary_df, rules_df = grading_utils.generate_export_data(df)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            detail_df.to_excel(writer, sheet_name='明细表', index=False)
            summary_df.to_excel(writer, sheet_name='汇总表', index=False)
            rules_df.to_excel(writer, sheet_name='规则校验', index=False)
        
        output.seek(0)
        
        # Save to a temp file to serve
        # Use absolute path for download_path
        download_path = os.path.join(BASE_DIR, "download_result.xlsx")
        
        # Write bytes
        with open(download_path, "wb") as f:
            f.write(output.getvalue())
            
        return FileResponse(download_path, filename="grading_result.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/api/cockpit-upload")
async def cockpit_upload(file: UploadFile = File(...), date: str = Form(...)):
    try:
        content = await file.read()
        
        # 1. Save to local file (optional backup)
        excel_data = io.BytesIO(content)
        # Use pandas to verify it's a valid excel and get sheets
        xl = pd.ExcelFile(excel_data)
        
        # 2. Insert into MySQL
        from sqlalchemy import create_engine
        import urllib.parse
        
        # DB Config
        DB_USER = "ycdb"
        DB_PASSWORD = "Jxyc1234!"
        DB_HOST = "192.168.113.14"
        DB_PORT = "3307"
        DB_NAME = "selfdata"
        
        # URL Encode password to handle special characters safely
        encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
        
        # SQLAlchemy connection string
        # Added charset to match JDBC params like allowPublicKeyRetrieval
        db_url = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        
        # Remove connect_args for now as it might cause issues with some drivers/versions
        # or pymysql might not support it directly in create_engine this way.
        # But 'allow_public_key_retrieval' is a valid connection arg for pymysql.
        # The error "Connection.__init__() got an unexpected keyword argument 'allow_public_key_retrieval'"
        # suggests that the installed pymysql version or the way sqlalchemy passes it is not compatible.
        # 
        # Fix: Pass it via the query string in the URL or check pymysql version.
        # Or simply remove it if not strictly needed (usually needed for caching_sha2_password with RSA).
        # Alternatively, try passing it in the query string of the URL if supported by pymysql.
        # db_url = f"...?charset=utf8mb4&allow_public_key_retrieval=true"
        
        # Let's try adding it to the URL query parameters instead of connect_args
        # Pymysql might not accept it as a kwarg in __init__ but maybe as part of the connection dict?
        # Actually, for pymysql, it is often not needed if we are not using SSL or specific auth plugins?
        # But DBeaver used it.
        # Let's try to remove it first. If it fails with "Public Key Retrieval is not allowed", then we add it back differently.
        
        engine = create_engine(db_url)
        
        # --- 0. Delete existing data for the selected date (Idempotency) ---
        from sqlalchemy import text
        with engine.begin() as conn:
             # Delete from grading_data
             conn.execute(text("DELETE FROM grading_data WHERE date_str = :date"), {"date": date})
             # Delete from grading_line
             conn.execute(text("DELETE FROM grading_line WHERE date_str = :date"), {"date": date})
        
        # Need to read specific sheets: '明细表' -> grading_data, '汇总表' -> grading_line
        # Requirement says: "上传数据表后（含有明细表和汇总表...）... 插入到MySQL数据库中"
        # Table `grading_data` matches `明细表` structure (License No, Scores, etc.)
        # Table `grading_line` matches `汇总表` structure (New Level, Score Line, etc.)
        
        # --- Process 明细表 -> grading_data ---
        if '明细表' in xl.sheet_names:
            df_detail = pd.read_excel(excel_data, sheet_name='明细表')
            
            # Map columns from Excel to DB
            # Excel Columns: 许可证号, 原档位, 新档位, 档位编码, 卷烟购进金额指标值, ...
            # DB Columns: license_no, original_level, new_level, level_code, purchase_amount_val, ...
            
            # Create a mapping dict based on inspection
            col_map_detail = {
                '许可证号': 'license_no',
                '原档位': 'original_level',
                '新档位': 'new_level',
                '档位编码': 'level_code',
                '卷烟购进金额指标值': 'purchase_amount_val',
                '卷烟购进金额指标排名': 'purchase_amount_rank',
                '卷烟购进金额得分': 'purchase_amount_score',
                '信用等级指标值': 'credit_rating_val',
                '信用等级指标得分': 'credit_rating_score',
                '专柜陈列得分': 'counter_display_score',
                '摆放规则得分': 'placement_rule_score',
                '破损褪色得分': 'damage_crease_score', # Note: DB says '破损褶皱', Excel says '破损褪色' - Assuming match
                '主题陈列得分': 'theme_display_score',
                '明码标价得分': 'pricing_tag_score',
                '交易数据指标值': 'transaction_data_val',
                '交易数据指标得分': 'transaction_data_score',
                '消费环境得分': 'consumption_env_score',
                '营销线路': 'marketing_route',
                '总分': 'total_score',
                '总分排名': 'total_score_rank',
                '所属区县': 'district'
            }
            
            # Rename columns
            df_to_db_detail = df_detail.rename(columns=col_map_detail)
            
            # Filter only columns that exist in DB to avoid errors
            # We can select only the mapped columns + Date
            valid_cols = list(col_map_detail.values())
            
            # Add 'date_str' from request
            df_to_db_detail['date_str'] = date
            
            # Keep only valid columns that are present in the renamed df
            final_cols_detail = [c for c in valid_cols if c in df_to_db_detail.columns] + ['date_str']
            df_to_db_detail = df_to_db_detail[final_cols_detail]
            
            # Insert into DB
            # Use 'append' to add to existing table
            # chunksize optimization to avoid hitting max_questions limits if possible?
            # Actually max_questions is queries per hour. Chunking reduces query count if using multi-value insert.
            # to_sql by default uses executemany or multi-value insert depending on 'method'.
            # 'multi' method inserts multiple rows in one INSERT statement.
            # This significantly reduces the number of queries (questions).
            
            chunk_size = 1000 # Insert 1000 rows per query
            df_to_db_detail.to_sql('grading_data', con=engine, if_exists='append', index=False, chunksize=chunk_size, method='multi')
            
        # --- Process 汇总表 -> grading_line ---
        if '汇总表' in xl.sheet_names:
            df_summary = pd.read_excel(excel_data, sheet_name='汇总表')
            
            # Map columns
            # Excel: 客户类别(Grade Name), 分档线(Min Score)
            # DB: new_level, score, date_str, remark, remark1
            
            col_map_summary = {
                '客户类别': 'new_level',
                '分档线': 'score'
            }
            
            df_to_db_summary = df_summary.rename(columns=col_map_summary)
            
            df_to_db_summary['date_str'] = date
            df_to_db_summary['remark'] = ''
            df_to_db_summary['remark1'] = ''
            
            final_cols_summary = ['new_level', 'score', 'date_str', 'remark', 'remark1']
            # Ensure columns exist
            for c in final_cols_summary:
                if c not in df_to_db_summary.columns:
                    df_to_db_summary[c] = None
            
            df_to_db_summary = df_to_db_summary[final_cols_summary]
            
            # Use multi insert here too just in case
            df_to_db_summary.to_sql('grading_line', con=engine, if_exists='append', index=False, method='multi')

        return {"message": "上传数据成功！"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"DB Upload Failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
