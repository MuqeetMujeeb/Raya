from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    local_path = Column(String)
    file_count = Column(Integer, default=0)
    language_distribution = Column(JSON)
    structure = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="processing")  # processing, completed, failed
    
class CodeFile(Base):
    __tablename__ = "code_files"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, index=True)
    file_path = Column(String)
    language = Column(String)
    content = Column(Text)
    parsed_data = Column(JSON)
    functions = Column(JSON)
    classes = Column(JSON)
    imports = Column(JSON)
    lines_of_code = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class ParsedFunction(Base):
    __tablename__ = "parsed_functions"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, index=True)
    name = Column(String)
    start_line = Column(Integer)
    end_line = Column(Integer)
    parameters = Column(JSON)
    return_type = Column(String)
    docstring = Column(Text)
    complexity = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class ParsedClass(Base):
    __tablename__ = "parsed_classes"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, index=True)
    name = Column(String)
    start_line = Column(Integer)
    end_line = Column(Integer)
    methods = Column(JSON)
    attributes = Column(JSON)
    inheritance = Column(JSON)
    docstring = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)