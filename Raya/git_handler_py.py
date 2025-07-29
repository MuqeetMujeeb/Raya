import os
import shutil
import tempfile
import zipfile
from urllib.parse import urlparse
from git import Repo
from git.exc import GitCommandError
from typing import Optional, Dict, Any
import logging
from config import Config

logger = logging.getLogger(__name__)

class GitHandler:
    def __init__(self):
        self.temp_dir = Config.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def clone_repository(self, repo_url: str) -> Dict[str, Any]:
        """Clone a Git repository and return metadata"""
        try:
            # Validate URL
            if not self._is_valid_git_url(repo_url):
                raise ValueError("Invalid Git repository URL")
            
            # Create temporary directory
            temp_path = tempfile.mkdtemp(dir=self.temp_dir)
            
            # Clone repository
            repo = Repo.clone_from(repo_url, temp_path)
            
            # Get repository metadata
            metadata = self._extract_repo_metadata(repo, temp_path)
            metadata['local_path'] = temp_path
            metadata['source'] = 'git'
            
            return metadata
            
        except GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            raise Exception(f"Failed to clone repository: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during clone: {e}")
            raise Exception(f"Error processing repository: {str(e)}")
    
    def extract_zip_file(self, zip_path: str) -> Dict[str, Any]:
        """Extract ZIP file and return metadata"""
        try:
            # Create temporary directory
            temp_path = tempfile.mkdtemp(dir=self.temp_dir)
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # Get the main directory (handle GitHub zip structure)
            extracted_items = os.listdir(temp_path)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_path, extracted_items[0])):
                main_dir = os.path.join(temp_path, extracted_items[0])
            else:
                main_dir = temp_path
            
            # Get metadata
            metadata = self._extract_directory_metadata(main_dir)
            metadata['local_path'] = main_dir
            metadata['source'] = 'zip'
            
            return metadata
            
        except zipfile.BadZipFile:
            raise Exception("Invalid ZIP file")
        except Exception as e:
            logger.error(f"ZIP extraction failed: {e}")
            raise Exception(f"Error extracting ZIP file: {str(e)}")
    
    def _is_valid_git_url(self, url: str) -> bool:
        """Validate Git repository URL"""
        try:
            parsed = urlparse(url)
            
            # Check for common Git hosting services
            valid_hosts = ['github.com', 'gitlab.com', 'bitbucket.org']
            if parsed.netloc.lower() in valid_hosts:
                return True
            
            # Check for .git extension
            if url.endswith('.git'):
                return True
            
            # Check for SSH format
            if url.startswith('git@'):
                return True
            
            return False
        except:
            return False
    
    def _extract_repo_metadata(self, repo: Repo, path: str) -> Dict[str, Any]:
        """Extract metadata from Git repository"""
        try:
            # Get basic repo info
            remote_url = repo.remote().url if repo.remotes else None
            
            # Get latest commit info
            latest_commit = repo.head.commit
            
            # Get repository structure
            structure = self._get_directory_structure(path)
            
            # Get language distribution
            language_dist = self._get_language_distribution(path)
            
            # Count files
            file_count = self._count_code_files(path)
            
            return {
                'name': os.path.basename(path),
                'url': remote_url,
                'latest_commit': latest_commit.hexsha,
                'commit_message': latest_commit.message.strip(),
                'author': latest_commit.author.name,
                'commit_date': latest_commit.committed_datetime.isoformat(),
                'structure': structure,
                'language_distribution': language_dist,
                'file_count': file_count,
                'branch': repo.active_branch.name if repo.active_branch else 'main'
            }
        except Exception as e:
            logger.error(f"Error extracting repo metadata: {e}")
            return self._extract_directory_metadata(path)
    
    def _extract_directory_metadata(self, path: str) -> Dict[str, Any]:
        """Extract metadata from directory (for non-git sources)"""
        structure = self._get_directory_structure(path)
        language_dist = self._get_language_distribution(path)
        file_count = self._count_code_files(path)
        
        return {
            'name': os.path.basename(path),
            'url': None,
            'structure': structure,
            'language_distribution': language_dist,
            'file_count': file_count
        }
    
    def _get_directory_structure(self, path: str) -> Dict[str, Any]:
        """Get directory structure as nested dict"""
        def build_tree(directory):
            tree = {}
            try:
                for item in os.listdir(directory):
                    if item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(directory, item)
                    if os.path.isdir(item_path):
                        tree[item] = build_tree(item_path)
                    else:
                        # Only include code files
                        if self._is_code_file(item):
                            tree[item] = {
                                'type': 'file',
                                'size': os.path.getsize(item_path),
                                'extension': os.path.splitext(item)[1]
                            }
            except PermissionError:
                pass
            return tree
        
        return build_tree(path)
    
    def _get_language_distribution(self, path: str) -> Dict[str, int]:
        """Get distribution of programming languages"""
        language_count = {}
        
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if self._is_code_file(file):
                    ext = os.path.splitext(file)[1]
                    language = self._get_language_from_extension(ext)
                    if language:
                        language_count[language] = language_count.get(language, 0) + 1
        
        return language_count
    
    def _count_code_files(self, path: str) -> int:
        """Count total number of code files"""
        count = 0
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if self._is_code_file(file):
                    count += 1
        return count
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in Config.ALLOWED_EXTENSIONS
    
    def _get_language_from_extension(self, ext: str) -> Optional[str]:
        """Get programming language from file extension"""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP'
        }
        return language_map.get(ext.lower())
    
    def cleanup_temp_directory(self, path: str) -> None:
        """Clean up temporary directory"""
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
        except Exception as e:
            logger.error(f"Failed to cleanup directory {path}: {e}")
    
    def get_file_list(self, path: str) -> list:
        """Get list of all code files in the repository"""
        files = []
        
        for root, dirs, filenames in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for filename in filenames:
                if self._is_code_file(filename):
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(full_path, path)
                    files.append({
                        'path': relative_path,
                        'full_path': full_path,
                        'language': self._get_language_from_extension(os.path.splitext(filename)[1]),
                        'size': os.path.getsize(full_path)
                    })
        
        return files