from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import tempfile
import os
import shutil
import logging
from datetime import datetime

from database import get_db
from code_parser import CodeParser
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CodePilot API",
    description="Code parsing and analysis API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CodePilot API",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/analyze/repository")
async def analyze_repository(
    repo_url: str = Form(...),
    db: Session = Depends(get_db)
):
    """Analyze a Git repository by URL"""
    try:
        logger.info(f"Starting analysis of repository: {repo_url}")
        
        # Initialize code parser
        parser = CodeParser(db)
        
        # Process repository
        result = parser.process_repository(repo_url=repo_url)
        
        logger.info(f"Repository analysis completed: {result['repository_id']}")
        
        return {
            "success": True,
            "message": "Repository analyzed successfully",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Repository analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Analyze uploaded ZIP file"""
    try:
        # Validate file
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only ZIP files are supported")
        
        if file.size > Config.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        logger.info(f"Starting analysis of uploaded file: {file.filename}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
        
        try:
            # Initialize code parser
            parser = CodeParser(db)
            
            # Process ZIP file
            result = parser.process_repository(zip_file_path=temp_file_path)
            
            logger.info(f"Upload analysis completed: {result['repository_id']}")
            
            return {
                "success": True,
                "message": "ZIP file analyzed successfully",
                "data": result
            }
            
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repository/{repo_id}")
async def get_repository_analysis(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed analysis of a repository"""
    try:
        parser = CodeParser(db)
        result = parser.get_repository_analysis(repo_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get repository analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repository/{repo_id}/files")
async def get_repository_files(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Get list of files in repository"""
    try:
        parser = CodeParser(db)
        result = parser.get_repository_analysis(repo_id)
        
        return {
            "success": True,
            "data": {
                "repository_id": repo_id,
                "files": result['files']
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get repository files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/file/{file_id}")
async def get_file_content(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed content of a specific file"""
    try:
        parser = CodeParser(db)
        result = parser.get_file_content(file_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repository/{repo_id}/structure")
async def get_repository_structure(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Get repository structure"""
    try:
        parser = CodeParser(db)
        result = parser.get_repository_analysis(repo_id)
        
        return {
            "success": True,
            "data": {
                "repository_id": repo_id,
                "structure": result['repository']['structure'],
                "language_distribution": result['repository']['language_distribution']
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get repository structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repository/{repo_id}/statistics")
async def get_repository_statistics(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """Get repository statistics"""
    try:
        parser = CodeParser(db)
        result = parser.get_repository_analysis(repo_id)
        
        return {
            "success": True,
            "data": {
                "repository_id": repo_id,
                "statistics": result['statistics']
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get repository statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Create temp directory
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    
    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG,
        log_level="info"
    )