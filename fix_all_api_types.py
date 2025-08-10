#!/usr/bin/env python3
"""
API型アノテーションとlintエラーを完全修正
"""

import os
import re

def fix_file(filepath):
    """ファイルの型アノテーションとlintエラーを修正"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # typing imports の修正
    # 完全削除するパターン
    content = re.sub(r'from typing import .*(?:Dict|List|Optional|Union|Tuple|Set).*\n', '', content)
    
    # Anyだけ残すパターン
    content = re.sub(r'from typing import Any,?\s*(?:Dict|List|Optional|Union|Tuple|Set).*\n', 'from typing import Any\n', content)
    content = re.sub(r'from typing import (?:Dict|List|Optional|Union|Tuple|Set).*,\s*Any\n', 'from typing import Any\n', content)
    
    # 型アノテーションの変更 - より包括的なパターン
    # Optional[X] -> X | None
    content = re.sub(r'Optional\[([^\[\]]+(?:\[[^\[\]]+\])?)\]', r'\1 | None', content)
    
    # List[X] -> list[X]
    content = re.sub(r'List\[([^\[\]]+(?:\[[^\[\]]+\])?)\]', r'list[\1]', content)
    
    # Dict[X, Y] -> dict[X, Y]
    content = re.sub(r'Dict\[([^,\[\]]+(?:\[[^,\[\]]+\])?),\s*([^\[\]]+(?:\[[^\[\]]+\])?)\]', r'dict[\1, \2]', content)
    
    # Tuple[X, ...] -> tuple[X, ...]
    content = re.sub(r'Tuple\[([^\[\]]+(?:\[[^\[\]]+\])?)\]', r'tuple[\1]', content)
    
    # Set[X] -> set[X]
    content = re.sub(r'Set\[([^\[\]]+(?:\[[^\[\]]+\])?)\]', r'set[\1]', content)
    
    # Union[X, Y] -> X | Y
    content = re.sub(r'Union\[([^,\[\]]+),\s*([^\[\]]+)\]', r'\1 | \2', content)
    
    # 空白行の余分な空白を削除 (W293)
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        # 空白のみの行は空行にする
        if line and line.isspace():
            new_lines.append('')
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # 空のimport文を削除
    content = re.sub(r'from typing import\s*\n', '', content)
    
    # 連続する空行を2つまでに制限
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # 特定のファイルに対する追加修正
    if 'auth.py' in filepath:
        # anyをAnyに修正
        content = re.sub(r'dict\[str, any\]', 'dict[str, Any]', content)
    
    if 'prediction.py' in filepath:
        # print文をloggerに置換（T201エラー対応）
        content = re.sub(r'(\s*)print\((.*?)\)', r'\1logger.debug(\2)', content)
        # loggerインポート追加（まだなければ）
        if 'from loguru import logger' not in content and 'logger.debug' in content:
            # 最初のimport文の後に追加
            import_lines = []
            other_lines = []
            found_imports = False
            for line in content.split('\n'):
                if line.startswith('import ') or line.startswith('from '):
                    import_lines.append(line)
                    found_imports = True
                elif found_imports and line and not line.startswith('import ') and not line.startswith('from '):
                    # import文が終わった
                    import_lines.append('from loguru import logger')
                    other_lines.append(line)
                    found_imports = False
                else:
                    other_lines.append(line)
            
            if import_lines:
                content = '\n'.join(import_lines + other_lines)
    
    if 'websocket' in filepath or 'connection_manager' in filepath:
        # logging.error -> logging.exception in except blocks (TRY400)
        # except節内のlogging.errorをlogging.exceptionに変更
        lines = content.split('\n')
        new_lines = []
        in_except = False
        
        for i, line in enumerate(lines):
            if 'except' in line and ':' in line:
                in_except = True
            elif in_except and line and not line.startswith(' ') and not line.startswith('\t'):
                in_except = False
            
            if in_except and 'logging.error' in line:
                line = line.replace('logging.error', 'logging.exception')
            
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    # 変更があった場合のみ書き込み
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """メイン処理"""
    api_dir = 'src/api'
    
    modified_files = []
    
    for root, dirs, files in os.walk(api_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    modified_files.append(filepath)
                    print(f"Fixed: {filepath}")
    
    # 特徴量抽出ファイルも修正
    feature_files = [
        'src/features/extractors/horse_performance.py',
        'src/features/extractors/jockey_trainer.py',
        'src/features/extractors/time_features.py'
    ]
    
    for filepath in feature_files:
        if os.path.exists(filepath):
            if fix_file(filepath):
                modified_files.append(filepath)
                print(f"Fixed: {filepath}")
    
    print(f"\nTotal files modified: {len(modified_files)}")

if __name__ == '__main__':
    main()