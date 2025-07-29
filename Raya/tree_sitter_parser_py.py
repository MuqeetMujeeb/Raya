import os
import tree_sitter
from tree_sitter import Language, Parser
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TreeSitterParser:
    def __init__(self):
        self.languages = {}
        self.parsers = {}
        self._setup_languages()
    
    def _setup_languages(self):
        """Setup tree-sitter languages"""
        try:
            # Language configurations
            language_configs = {
                'python': 'tree_sitter_python',
                'javascript': 'tree_sitter_javascript', 
                'typescript': 'tree_sitter_typescript',
                'java': 'tree_sitter_java',
                'cpp': 'tree_sitter_cpp',
                'c': 'tree_sitter_cpp',
                'go': 'tree_sitter_go',
                'rust': 'tree_sitter_rust'
            }
            
            # Initialize languages
            for lang_name, module_name in language_configs.items():
                try:
                    # Dynamic import
                    module = __import__(module_name)
                    self.languages[lang_name] = Language(module.language())
                    
                    # Create parser
                    parser = Parser()
                    parser.set_language(self.languages[lang_name])
                    self.parsers[lang_name] = parser
                    
                except Exception as e:
                    logger.warning(f"Failed to setup {lang_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to setup tree-sitter languages: {e}")
    
    def parse_file(self, file_path: str, language: str = None) -> Dict[str, Any]:
        """Parse a single file and extract code elements"""
        try:
            # Auto-detect language if not provided
            if not language:
                language = self._detect_language(file_path)
            
            if not language or language not in self.parsers:
                return self._fallback_parse(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse with tree-sitter
            tree = self.parsers[language].parse(bytes(content, 'utf-8'))
            
            # Extract elements based on language
            if language == 'python':
                return self._parse_python(tree, content)
            elif language in ['javascript', 'typescript']:
                return self._parse_javascript(tree, content)
            elif language == 'java':
                return self._parse_java(tree, content)
            elif language in ['cpp', 'c']:
                return self._parse_cpp(tree, content)
            elif language == 'go':
                return self._parse_go(tree, content)
            elif language == 'rust':
                return self._parse_rust(tree, content)
            else:
                return self._fallback_parse(file_path)
                
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return self._fallback_parse(file_path)
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust'
        }
        
        return extension_map.get(ext)
    
    def _parse_python(self, tree, content: str) -> Dict[str, Any]:
        """Parse Python code"""
        result = {
            'language': 'python',
            'functions': [],
            'classes': [],
            'imports': [],
            'variables': [],
            'errors': []
        }
        
        lines = content.split('\n')
        
        def traverse_node(node):
            if node.type == 'function_definition':
                func_info = self._extract_python_function(node, lines)
                if func_info:
                    result['functions'].append(func_info)
            
            elif node.type == 'class_definition':
                class_info = self._extract_python_class(node, lines)
                if class_info:
                    result['classes'].append(class_info)
            
            elif node.type in ['import_statement', 'import_from_statement']:
                import_info = self._extract_python_import(node, lines)
                if import_info:
                    result['imports'].append(import_info)
            
            elif node.type == 'assignment':
                var_info = self._extract_python_variable(node, lines)
                if var_info:
                    result['variables'].append(var_info)
            
            # Recursively traverse children
            for child in node.children:
                traverse_node(child)
        
        traverse_node(tree.root_node)
        return result
    
    def _extract_python_function(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract Python function information"""
        try:
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            
            # Find function name
            name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break
            
            if not name_node:
                return None
            
            func_name = lines[name_node.start_point[0]][name_node.start_point[1]:name_node.end_point[1]]
            
            # Extract parameters
            parameters = []
            params_node = None
            for child in node.children:
                if child.type == 'parameters':
                    params_node = child
                    break
            
            if params_node:
                for param_child in params_node.children:
                    if param_child.type == 'identifier':
                        param_name = lines[param_child.start_point[0]][param_child.start_point[1]:param_child.end_point[1]]
                        parameters.append(param_name)
            
            # Extract docstring
            docstring = None
            body_node = None
            for child in node.children:
                if child.type == 'block':
                    body_node = child
                    break
            
            if body_node and body_node.children:
                first_stmt = body_node.children[1] if len(body_node.children) > 1 else None
                if first_stmt and first_stmt.type == 'expression_statement':
                    expr_child = first_stmt.children[0] if first_stmt.children else None
                    if expr_child and expr_child.type == 'string':
                        docstring = lines[expr_child.start_point[0]][expr_child.start_point[1]:expr_child.end_point[1]]
            
            return {
                'name': func_name,
                'start_line': start_line + 1,
                'end_line': end_line + 1,
                'parameters': parameters,
                'docstring': docstring,
                'complexity': self._calculate_complexity(node)
            }
            
        except Exception as e:
            logger.error(f"Error extracting Python function: {e}")
            return None
    
    def _extract_python_class(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract Python class information"""
        try:
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            
            # Find class name
            name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break
            
            if not name_node:
                return None
            
            class_name = lines[name_node.start_point[0]][name_node.start_point[1]:name_node.end_point[1]]
            
            # Extract methods
            methods = []
            body_node = None
            for child in node.children:
                if child.type == 'block':
                    body_node = child
                    break
            
            if body_node:
                for child in body_node.children:
                    if child.type == 'function_definition':
                        method_info = self._extract_python_function(child, lines)
                        if method_info:
                            methods.append(method_info)
            
            return {
                'name': class_name,
                'start_line': start_line + 1,
                'end_line': end_line + 1,
                'methods': methods,
                'attributes': []  # TODO: Extract attributes
            }
            
        except Exception as e:
            logger.error(f"Error extracting Python class: {e}")
            return None
    
    def _extract_python_import(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract Python import information"""
        try:
            start_line = node.start_point[0]
            import_text = lines[start_line][node.start_point[1]:node.end_point[1]]
            
            return {
                'type': node.type,
                'statement': import_text,
                'line': start_line + 1
            }
            
        except Exception as e:
            logger.error(f"Error extracting Python import: {e}")
            return None
    
    def _extract_python_variable(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract Python variable information"""
        try:
            start_line = node.start_point[0]
            
            # Find variable name
            left_node = node.children[0] if node.children else None
            if left_node and left_node.type == 'identifier':
                var_name = lines[left_node.start_point[0]][left_node.start_point[1]:left_node.end_point[1]]
                
                return {
                    'name': var_name,
                    'line': start_line + 1,
                    'type': 'variable'
                }
            
        except Exception as e:
            logger.error(f"Error extracting Python variable: {e}")
            return None
    
    def _parse_javascript(self, tree, content: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript code"""
        result = {
            'language': 'javascript',
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': [],
            'variables': [],
            'errors': []
        }
        
        lines = content.split('\n')
        
        def traverse_node(node):
            if node.type in ['function_declaration', 'function_expression', 'arrow_function']:
                func_info = self._extract_js_function(node, lines)
                if func_info:
                    result['functions'].append(func_info)
            
            elif node.type == 'class_declaration':
                class_info = self._extract_js_class(node, lines)
                if class_info:
                    result['classes'].append(class_info)
            
            elif node.type in ['import_statement', 'import_clause']:
                import_info = self._extract_js_import(node, lines)
                if import_info:
                    result['imports'].append(import_info)
            
            # Recursively traverse children
            for child in node.children:
                traverse_node(child)
        
        traverse_node(tree.root_node)
        return result
    
    def _extract_js_function(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract JavaScript function information"""
        try:
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            
            # Extract function name
            func_name = "anonymous"
            for child in node.children:
                if child.type == 'identifier':
                    func_name = lines[child.start_point[0]][child.start_point[1]:child.end_point[1]]
                    break
            
            return {
                'name': func_name,
                'start_line': start_line + 1,
                'end_line': end_line + 1,
                'parameters': [],  # TODO: Extract parameters
                'type': node.type
            }
            
        except Exception as e:
            logger.error(f"Error extracting JavaScript function: {e}")
            return None
    
    def _extract_js_class(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract JavaScript class information"""
        try:
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            
            # Extract class name
            class_name = "anonymous"
            for child in node.children:
                if child.type == 'identifier':
                    class_name = lines[child.start_point[0]][child.start_point[1]:child.end_point[1]]
                    break
            
            return {
                'name': class_name,
                'start_line': start_line + 1,
                'end_line': end_line + 1,
                'methods': []  # TODO: Extract methods
            }
            
        except Exception as e:
            logger.error(f"Error extracting JavaScript class: {e}")
            return None
    
    def _extract_js_import(self, node, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Extract JavaScript import information"""
        try:
            start_line = node.start_point[0]
            import_text = lines[start_line][node.start_point[1]:node.end_point[1]]
            
            return {
                'statement': import_text,
                'line': start_line + 1
            }
            
        except Exception as e:
            logger.error(f"Error extracting JavaScript import: {e}")
            return None
    
    def _parse_java(self, tree, content: str) -> Dict[str, Any]:
        """Parse Java code - basic implementation"""
        return {
            'language': 'java',
            'functions': [],
            'classes': [],
            'imports': [],
            'errors': []
        }
    
    def _parse_cpp(self, tree, content: str) -> Dict[str, Any]:
        """Parse C++ code - basic implementation"""
        return {
            'language': 'cpp',
            'functions': [],
            'classes': [],
            'includes': [],
            'errors': []
        }
    
    def _parse_go(self, tree, content: str) -> Dict[str, Any]:
        """Parse Go code - basic implementation"""
        return {
            'language': 'go',
            'functions': [],
            'structs': [],
            'imports': [],
            'errors': []
        }
    
    def _parse_rust(self, tree, content: str) -> Dict[str, Any]:
        """Parse Rust code - basic implementation"""
        return {
            'language': 'rust',
            'functions': [],
            'structs': [],
            'imports': [],
            'errors': []
        }
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        def traverse_for_complexity(n):
            nonlocal complexity
            if n.type in ['if_statement', 'while_statement', 'for_statement', 'except_clause']:
                complexity += 1
            for child in n.children:
                traverse_for_complexity(child)
        
        traverse_for_complexity(node)
        return complexity
    
    def _fallback_parse(self, file_path: str) -> Dict[str, Any]:
        """Fallback parsing for unsupported languages"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            language = self._detect_language(file_path) or 'unknown'
            
            return {
                'language': language,
                'functions': [],
                'classes': [],
                'imports': [],
                'lines_of_code': len([line for line in lines if line.strip()]),
                'total_lines': len(lines),
                'errors': ['Fallback parsing used - limited functionality']
            }
            
        except Exception as e:
            logger.error(f"Fallback parsing failed for {file_path}: {e}")
            return {
                'language': 'unknown',
                'functions': [],
                'classes': [],
                'imports': [],
                'errors': [f'Parsing failed: {str(e)}']
            }
    
    def batch_parse_files(self, file_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Parse multiple files in batch"""
        results = {}
        
        for file_info in file_list:
            file_path = file_info['full_path']
            language = file_info['language']
            
            try:
                parsed_result = self.parse_file(file_path, language)
                parsed_result['file_info'] = file_info
                results[file_info['path']] = parsed_result
                
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                results[file_info['path']] = {
                    'language': language or 'unknown',
                    'functions': [],
                    'classes': [],
                    'imports': [],
                    'errors': [f'Parsing failed: {str(e)}'],
                    'file_info': file_info
                }
        
        return results