import os

def count_lines():
    files_info = []
    for root, dirs, files in os.walk('bot'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        files_info.append((len(lines), filepath))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    
    # Sort files by line count in descending order
    files_info.sort(reverse=True, key=lambda x: x[0])
    for count, path in files_info:
        print(f"{count:<5} {path}")

if __name__ == '__main__':
    count_lines()
