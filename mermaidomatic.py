import os
import ast
import pytz
import logging
from datetime import datetime
from collections import defaultdict
from typing import Union, Dict, List

# Setup Logging
logging.basicConfig(level=logging.INFO)

def validate_file_path(file_path: str) -> Union[bool, str]:
    if not os.path.exists(file_path):
        return "File does not exist."
    if not file_path.endswith('.py'):
        return "Not a Python file."
    return True

def parse_python_file(file_path: str) -> ast.AST:
    with open(file_path, 'r') as f:
        return ast.parse(f.read())

def analyze_ast(ast_tree: ast.AST) -> Dict:
    analysis, function_calls, function_details = [], defaultdict(list), defaultdict(dict)
    
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.FunctionDef):
            analysis.append(node.name)
            return_types = set()
            for sub_node in ast.walk(node):
                if isinstance(sub_node, ast.Return):
                    if sub_node.value:
                        return_types.add(type(sub_node.value).__name__)
            
            function_details[node.name] = {
                'params': [arg.arg for arg in node.args.args],
                'returns': ', '.join(return_types) if return_types else 'None',
                'docstring': ast.get_docstring(node, clean=True)
            }
            
            in_loop = False
            for sub_node in ast.walk(node):
                if isinstance(sub_node, (ast.For, ast.While)):
                    in_loop = True
                if isinstance(sub_node, ast.Call) and isinstance(sub_node.func, ast.Name) and sub_node.func.id in analysis:
                    params_passed = [
                        arg.id if isinstance(arg, ast.Name) else arg.value if isinstance(arg, ast.Constant) else type(arg).__name__
                        for arg in sub_node.args
                    ]
                    function_calls[node.name].append((sub_node.func.id, in_loop, params_passed))
    
    return analysis, function_calls, function_details

def generate_mermaid_syntax(analysis, function_calls, function_details) -> str:
    syntax = "```mermaid\ngraph TD;\n"
    
    for func in analysis:
        details = function_details[func]
        params = f"\\n\\nPARAMS: {', '.join(details['params'])}"
        returns = f"\\n\\nRETURNS: {details['returns'] if details['returns'] else 'None'}"
        docstring = f"\\n\\nDOC: {details['docstring'] if details['docstring'] else 'None'}"
        syntax += f"{func}({func}{params}{returns}{docstring})\n"

    for func, calls in function_calls.items():
        for call, in_loop, params_passed in calls:
            label = f"{ 'in_loop' if in_loop else 'calls' } params: {', '.join(params_passed)}"
            syntax += f"{func}-->|\"{label}\"|{call};\n"
    
    return syntax + "```"

def write_to_markdown(syntax: str, output_path: str, file_path: str) -> None:
    current_time = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    with open(output_path, 'w') as f:
        f.write(f"# Generated Mermaid.js Diagram\n\n**File Name:** {os.path.basename(file_path)}\n")
        f.write(f"**Date and Time of Diagram Generation:** {current_time}\n\n{syntax}")

def main(file_path: str, output_path: str) -> None:
    validation_result = validate_file_path(file_path)
    if validation_result is not True:
        logging.error(f"Validation failed: {validation_result}")
        return

    logging.info("Starting AST analysis...")
    ast_tree = parse_python_file(file_path)
    analysis, function_calls, function_details = analyze_ast(ast_tree)

    logging.info("Generating Mermaid.js syntax...")
    mermaid_syntax = generate_mermaid_syntax(analysis, function_calls, function_details)

    logging.info("Writing to Markdown file...")
    write_to_markdown(mermaid_syntax, output_path, file_path)
    logging.info("Process completed successfully.")

if __name__ == "__main__":
    main("example.py", "output.md")
