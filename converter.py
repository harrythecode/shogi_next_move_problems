import json
import os
import re
import requests
from datetime import datetime
from lxml import html
import urllib.parse

INPUT_FILE = "problem.txt"
JSON_OUTPUT = "problems.json"

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

def generate_problem(input_file, json_output):
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

    # Add problem data to JSON file
    with open(json_output, 'r+') as f:
        data = json.load(f)
        data["problems"].append(problem_data)
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.truncate()

def main():
    global INPUT_FILE  # グローバル変数として宣言

    # Initialize JSON file if it doesn't exist
    if not os.path.exists(JSON_OUTPUT):
        with open(JSON_OUTPUT, 'w') as f:
            json.dump({"problems": []}, f)

    # Process problems
    counter = 1
    while os.path.exists(INPUT_FILE):
        generate_problem(INPUT_FILE, JSON_OUTPUT)
        counter += 1
        INPUT_FILE = f"problem_{counter}.txt"

    # Update final problem count and last updated timestamp
    with open(JSON_OUTPUT, 'r+') as f:
        data = json.load(f)
        data["count"] = len(data["problems"])
        data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.truncate()

    print(f"JSONファイルを更新しました: {JSON_OUTPUT}")
    print("処理が完了しました。")

if __name__ == "__main__":
    main()