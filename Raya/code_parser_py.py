from typing import Dict, List, Any, Optional
import os
import logging
from git_handler import GitHandler
from tree_sitter_parser import TreeSitterParser
from models import Repository, CodeFile, ParsedFunction, ParsedClass
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

class CodeParser:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.git_handler = GitHandler()
        self.tree_sitter_parser = TreeSitterParser()
    
    def process_repository(self, repo_url: str = None, zip_file_path: str = None) -> Dict[str, Any]:
        """Process a repository from URL or ZIP file"""
        try:
            if repo_url:
                return self._process_git_repository(repo_url)
            elif zip_file_path:
                return self._process_zip_file(zip_file_path)
            else:
                raise ValueError("Either repo_url or zip_file_path must be provided")
                
        except Exception as e:
            logger.error(f"Failed to process repository: {e}")
            raise Exception(f"Repository processing failed: {str(e)}")
    
    def _process_git_repository(self, repo_url: str) -> Dict[str, Any]:
        """Process Git repository"""
        try:
            # Clone repository
            repo_metadata = self.git_handler.clone_repository(repo_url)
            
            # Save repository to database
            repo_record = self._save_repository_metadata(repo_metadata)
            
            # Parse code files
            parsing_results = self._parse_repository_files(repo_metadata['local_path'], repo_record.id)
            
            # Update repository status
            repo_record.status = "completed"
            self.db_session.commit()
            
            # Cleanup temporary files
            self.git_handler.cleanup_temp_directory(repo_metadata['local_path'])
            
            return {
                'repository_id': repo_record.id,
                'status': 'completed',
                'metadata': repo_metadata,
                'parsing_results': parsing_results
            }
            
        except Exception as e:
            logger.error(f"Git repository processing failed: {e}")
            raise e
    
    def _process_zip_file(self, zip_file_path: str) -> Dict[str, Any]:
        """Process ZIP file"""
        try:
            # Extract ZIP file
            repo_metadata = self.git_handler.extract_zip_file(zip_file_path)
            
            # Save repository to database
            repo_record = self._save_repository_metadata(repo_metadata)
            
            # Parse code files
            parsing_results = self._parse_repository_files(repo_metadata['local_path'], repo_record.id)
            
            # Update repository status
            repo_record.status = "completed"
            self.db_session.commit()
            
            # Cleanup temporary files
            self.git_handler.cleanup_temp_directory(repo_metadata['local_path'])
            
            return {
                'repository_id': repo_record.id,
                'status': 'completed',
                'metadata': repo_metadata,
                'parsing_results': parsing_results
            }
            
        except Exception as e:
            logger.error(f"ZIP file processing failed: {e}")
            raise e
    
    def _save_repository_metadata(self, metadata: Dict[str, Any]) -> Repository:
        """Save repository metadata to database"""
        try:
            repo = Repository(
                name=metadata['name'],
                url=metadata.get('url'),
                local_path=metadata['local_path'],
                file_count=metadata['file_count'],
                language_distribution=metadata['language_distribution'],
                structure=metadata['structure'],
                status="processing"
            )
            
            self.db_session.add(repo)
            self.db_session.commit()
            self.db_session.refresh(repo)
            
            return repo
            
        except Exception as e:
            logger.error(f"Failed to save repository metadata: {e}")
            self.db_session.rollback()
            raise e
    
    def _parse_repository_files(self, repo_path: str, repo_id: int) -> Dict[str, Any]:
        """Parse all code files in repository"""
        try:
            # Get list of code files
            file_list = self.git_handler.get_file_list(repo_path)
            
            if not file_list:
                return {
                    'total_files': 0,
                    'parsed_files': 0,
                    'errors': ['No code files found in repository']
                }
            
            # Parse files using tree-sitter
            parsing_results = self.tree_sitter_parser.batch_parse_files(file_list)
            
            # Save parsed results to database
            saved_files = 0
            parsing_errors = []
            
            for file_path, parsed_data in parsing_results.items():
                try:
                    self._save_parsed_file(repo_id, file_path, parsed_data)
                    saved_files += 1
                except Exception as e:
                    error_msg = f"Failed to save {file_path}: {str(e)}"
                    parsing_errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                'total_files': len(file_list),
                'parsed_files': saved_files,
                'errors': parsing_errors,
                'parsing_results': parsing_results
            }
            
        except Exception as e:
            logger.error(f"Failed to parse repository files: {e}")
            raise e
    
    def _save_parsed_file(self, repo_id: int, file_path: str, parsed_data: Dict[str, Any]) -> None:
        """Save parsed file data to database"""
        try:
            # Read file content
            full_path = parsed_data['file_info']['full_path']
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create CodeFile record
            code_file = CodeFile(
                repo_id=repo_id,
                file_path=file_path,
                language=parsed_data['language'],
                content=content,
                parsed_data=parsed_data,
                functions=parsed_data.get('functions', []),
                classes=parsed_data.get('classes', []),
                imports=parsed_data.get('imports', []),
                lines_of_code=parsed_data.get('lines_of_code', 0)
            )
            
            self.db_session.add(code_file)
            self.db_session.commit()
            self.db_session.refresh(code_file)
            
            # Save functions
            for func_data in parsed_data.get('functions', []):
                self._save_parsed_function(code_file.id, func_data)
            
            # Save classes
            for class_data in parsed_data.get('classes', []):
                self._save_parsed_class(code_file.id, class_data)
            
        except Exception as e:
            logger.error(f"Failed to save parsed file {file_path}: {e}")
            self.db_session.rollback()
            raise e
    
    def _save_parsed_function(self, file_id: int, func_data: Dict[str, Any]) -> None:
        """Save parsed function to database"""
        try:
            parsed_function = ParsedFunction(
                file_id=file_id,
                name=func_data['name'],
                start_line=func_data['start_line'],
                end_line=func_data['end_line'],
                parameters=func_data.get('parameters', []),
                docstring=func_data.get('docstring'),
                complexity=func_data.get('complexity', 1)
            )
            
            self.db_session.add(parsed_function)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save function {func_data.get('name', 'unknown')}: {e}")
            self.db_session.rollback()
    
    def _save_parsed_class(self, file_id: int, class_data: Dict[str, Any]) -> None:
        """Save parsed class to database"""
        try:
            parsed_class = ParsedClass(
                file_id=file_id,
                name=class_data['name'],
                start_line=class_data['start_line'],
                end_line=class_data['end_line'],
                methods=class_data.get('methods', []),
                attributes=class_data.get('attributes', []),
                docstring=class_data.get('docstring')
            )
            
            self.db_session.add(parsed_class)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save class {class_data.get('name', 'unknown')}: {e}")
            self.db_session.rollback()
    
    def get_repository_analysis(self, repo_id: int) -> Dict[str, Any]:
        """Get comprehensive analysis of a repository"""
        try:
            # Get repository
            repo = self.db_session.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                raise ValueError(f"Repository with id {repo_id} not found")
            
            # Get code files
            code_files = self.db_session.query(CodeFile).filter(CodeFile.repo_id == repo_id).all()
            
            # Get functions
            functions = self.db_session.query(ParsedFunction).join(CodeFile).filter(
                CodeFile.repo_id == repo_id
            ).all()
            
            # Get classes
            classes = self.db_session.query(ParsedClass).join(CodeFile).filter(
                CodeFile.repo_id == repo_id
            ).all()
            
            # Calculate statistics
            total_lines = sum(f.lines_of_code for f in code_files)
            avg_complexity = sum(f.complexity for f in functions) / len(functions) if functions else 0
            
            return {
                'repository': {
                    'id': repo.id,
                    'name': repo.name,
                    'url': repo.url,
                    'status': repo.status,
                    'created_at': repo.created_at.isoformat(),
                    'file_count': repo.file_count,
                    'language_distribution': repo.language_distribution,
                    'structure': repo.structure
                },
                'statistics': {
                    'total_files': len(code_files),
                    'total_functions': len(functions),
                    'total_classes': len(classes),
                    'total_lines_of_code': total_lines,
                    'average_complexity': round(avg_complexity, 2)
                },
                'files': [
                    {
                        'id': f.id,
                        'path': f.file_path,
                        'language': f.language,
                        'lines_of_code': f.lines_of_code,
                        'functions_count': len(f.functions),
                        'classes_count': len(f.classes)
                    }
                    for f in code_files
                ],
                'functions': [
                    {
                        'id': f.id,
                        'name': f.name,
                        'file_path': next(cf.file_path for cf in code_files if cf.id == f.file_id),
                        'start_line': f.start_line,
                        'end_line': f.end_line,
                        'parameters': f.parameters,
                        'complexity': f.complexity
                    }
                    for f in functions
                ],
                'classes': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'file_path': next(cf.file_path for cf in code_files if cf.id == c.file_id),
                        'start_line': c.start_line,
                        'end_line': c.end_line,
                        'methods_count': len(c.methods)
                    }
                    for c in classes
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get repository analysis: {e}")
            raise e
    
    def get_file_content(self, file_id: int) -> Dict[str, Any]:
        """Get detailed content of a specific file"""
        try:
            code_file = self.db_session.query(CodeFile).filter(CodeFile.id == file_id).first()
            if not code_file:
                raise ValueError(f"File with id {file_id} not found")
            
            # Get functions for this file
            functions = self.db_session.query(ParsedFunction).filter(
                ParsedFunction.file_id == file_id
            ).all()
            
            # Get classes for this file
            classes = self.db_session.query(ParsedClass).filter(
                ParsedClass.file_id == file_id
            ).all()
            
            return {
                'file': {
                    'id': code_file.id,
                    'path': code_file.file_path,
                    'language': code_file.language,
                    'content': code_file.content,
                    'lines_of_code': code_file.lines_of_code,
                    'parsed_data': code_file.parsed_data
                },
                'functions': [
                    {
                        'id': f.id,
                        'name': f.name,
                        'start_line': f.start_line,
                        'end_line': f.end_line,
                        'parameters': f.parameters,
                        'docstring': f.docstring,
                        'complexity': f.complexity
                    }
                    for f in functions
                ],
                'classes': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'start_line': c.start_line,
                        'end_line': c.end_line,
                        'methods': c.methods,
                        'attributes': c.attributes,
                        'docstring': c.docstring
                    }
                    for c in classes
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
            raise e