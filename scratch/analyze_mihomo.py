import ast

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            print(f"Function: {node.name} at line {node.lineno}")
        elif isinstance(node, ast.ClassDef):
            print(f"Class: {node.name} at line {node.lineno}")
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef) or isinstance(subnode, ast.AsyncFunctionDef):
                    print(f"  Method: {subnode.name} at line {subnode.lineno}")

if __name__ == '__main__':
    analyze_file('bot/modules/mihomo/monitor.py')
