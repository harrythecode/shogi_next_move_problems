import json
import os
import re
import requests
from datetime import datetime
from lxml import html
import urllib.parse

INPUT_FILE = "problem.txt"
RELEASES_INDEX = "releases/index.json"
PROBLEMS_PER_FILE = 100

def extract_info(html_content, field):
    tree = html.fromstring(html_content)
    xpath_queries = {
        "tournament": "//tr[th='Tournaments']/td/a/text()",
        "player1": "//tr[th='Players'][1]/td/a/text()",
        "player2": "//tr[th='Players'][2]/td/a/text()",
        "handicap": "//tr[th='Handicap']/td/text()",
        "strategy": "//tr[th='Strategy']/td/a/text()"
    }
    xpath_query = xpath_queries.get(field, f"//tr[th='{field}']/td/text()")
    result = tree.xpath(xpath_query)
    return result[0].strip() if result else ""

def debug_extract_info(html_content, field):
    result = extract_info(html_content, field)
    print(f"DEBUG: Extracting {field}: '{result}'")
    return result

def generate_problem(input_file, problem_count):
    with open(input_file, 'r') as f:
        url = f.readline().strip()

    response = requests.get(url)
    html_content = response.text

    # Extract information
    strategy = debug_extract_info(html_content, "strategy")
    tournament = debug_extract_info(html_content, "tournament")
    tournament_detail = debug_extract_info(html_content, "tournament_detail")
    player1 = debug_extract_info(html_content, "player1")
    player2 = debug_extract_info(html_content, "player2")
    handicap = debug_extract_info(html_content, "handicap")
    place = debug_extract_info(html_content, "place")
    time = debug_extract_info(html_content, "time")

    # Extract SFEN
    sfen_line = re.search(r'sfen=([^&]*)', url).group(1)
    sfen_trim = sfen_line.replace('+', ' ')
    sfen = urllib.parse.unquote(sfen_trim)

    # Generate ID
    id = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create problem data
    problem_data = {
        "id": id,
        "strategy": strategy,
        "type": "shogi_problem",
        "position": {"sfen": sfen},
        "analysis": {"url": url, "candidates": []},
        "metadata": {
            "tournament": tournament,
            "tournament_detail": tournament_detail,
            "player1": player1,
            "player2": player2,
            "handicap": handicap,
            "place": place,
            "time": time
        }
    }

    # Process candidates
    with open(input_file, 'r') as f:
        for line in f:
            if "検討" in line and "候補" in line:
                number = re.search(r'候補(\d+)', line).group(1)
                time = re.search(r'時間 (\S+)', line).group(1)
                depth = re.search(r'深さ (\S+)', line).group(1)
                nodes = re.search(r'ノード数 (\d+)', line).group(1)
                evaluation = re.search(r'評価値 (-?\d+)', line).group(1)
                best_line = re.search(r'読み筋 (.+)$', line).group(1).replace(' ', ',')

                candidate = {
                    "number": int(number),
                    "time": time,
                    "depth": depth,
                    "nodes": int(nodes),
                    "evaluation": int(evaluation),
                    "best_line": best_line
                }
                problem_data["analysis"]["candidates"].append(candidate)

    return problem_data

def update_releases_index(problem_count):
    with open(RELEASES_INDEX, 'r+') as f:
        data = json.load(f)
        file_index = (problem_count - 1) // PROBLEMS_PER_FILE
        filename = f"problems_{file_index * PROBLEMS_PER_FILE + 1}_{(file_index + 1) * PROBLEMS_PER_FILE}.json"
        
        if file_index >= len(data["problem_files"]):
            data["problem_files"].append({"filename": filename})
        
        data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.truncate()
    
    return filename

def update_or_create_problem_file(filename, new_problems):
    file_path = f"releases/{filename}"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        existing_problems = data.get("problems", [])
        
        # Update existing problems or add new ones
        problem_dict = {p["id"]: p for p in existing_problems}
        for new_problem in new_problems:
            problem_dict[new_problem["id"]] = new_problem
        
        updated_problems = list(problem_dict.values())
    else:
        updated_problems = new_problems

    with open(file_path, 'w') as f:
        json.dump({"problems": updated_problems, "count": len(updated_problems), "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}, f, ensure_ascii=False, indent=2)

def main():
    global INPUT_FILE

    problem_count = 0
    current_file = None
    current_problems = []

    while os.path.exists(INPUT_FILE):
        problem_data = generate_problem(INPUT_FILE, problem_count + 1)
        current_problems.append(problem_data)
        problem_count += 1

        if problem_count % PROBLEMS_PER_FILE == 0:
            output_file = update_releases_index(problem_count)
            update_or_create_problem_file(output_file, current_problems)
            current_problems = []

        INPUT_FILE = f"problem_{problem_count + 1}.txt"

    if current_problems:
        output_file = update_releases_index(problem_count)
        update_or_create_problem_file(output_file, current_problems)

    print(f"問題数: {problem_count}")
    print("releases/index.json を更新しました")
    print(f"releases/{output_file} を更新しました")
    print("処理が完了しました。")

if __name__ == "__main__":
    main()