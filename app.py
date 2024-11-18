from flask import Flask, render_template, request, abort
import os
from collections import defaultdict
import re
from fuzzywuzzy import fuzz
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords, wordnet

app = Flask(__name__)

# Function to parse main.txt and generate topics and subtopics
def parse_main_txt():
    with open("main.txt", "r") as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]
    
    topics = []
    current_topic = None

    for line in lines:
        if line[0].isdigit() and '.' in line:  # Topic line
            current_topic = {"name": line, "subtopics": []}
            topics.append(current_topic)
        elif current_topic:  # Subtopic line
            subtopic, description = map(str.strip, line.split(" - ", 1))
            filename = subtopic.replace(" ", "_") + ".txt"
            current_topic["subtopics"].append({"name": subtopic, "description": description, "file": filename.lower()})
    
    return topics

# Case-insensitive file search in the `/files` directory
def find_file(filename):
    for root, dirs, files in os.walk("files"):
        for file in files:
            if file.lower() == filename.lower():
                return os.path.join(root, file)
    return None

@app.route("/")
def index():
    topics = parse_main_txt()
    return render_template("index.html", topics=topics)

@app.route("/files/<path:filename>")
def files(filename):
    file_path = find_file(filename)
    if file_path:
        with open(file_path, "r") as file:
            content = file.read()
        return render_template("file_viewer.html", filename=filename, content=content)
    abort(404)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return render_template("search_results.html", query=query, results=[])

    results = []

    # Parse topics and subtopics
    with open("main.txt", "r") as file:
        content = file.read()

    current_topic = None
    subtopics = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+\.", line):  # Matches topics like "1. Manual Content Discovery"
            if current_topic:
                results.extend(search_subtopics(current_topic, subtopics, query))
            current_topic = line.split(".", 1)[1].strip()
            subtopics = []
        elif "-" in line:  # Subtopics with descriptions
            subtopics.append(line)
    
    if current_topic:
        results.extend(search_subtopics(current_topic, subtopics, query))

    # Sort results by relevance score
    for result in results:
        result['match_score'] = result.pop('score')  # Rename 'score' to 'match_score'

    results.sort(key=lambda x: x['match_score'], reverse=True)

    return render_template("search_results.html", query=query, results=results)

def search_subtopics(topic, subtopics, query):
    results = []
    for subtopic in subtopics:
        subtopic_name, description = [s.strip() for s in subtopic.split("-", 1)]
        file_path = find_file(subtopic_name.replace(" ", "_") + ".txt")
        score = calculate_relevance(query, topic, subtopic_name, description, file_path)
        if score > 0:
            results.append({
                "topic": topic,
                "subtopic": subtopic_name,
                "description": description,
                "score": score,
                "file": os.path.basename(file_path) if file_path else None,
            })
    return results


def calculate_relevance(query, topic, subtopic_name, description, file_path=None):
    # Assign weights for each field
    topic_weight = 0.5
    subtopic_weight = 1.0
    description_weight = 1.5
    file_weight = 2.0
    phrase_weight = 3.0

    # Tokenize and remove stopwords
    stop_words = set(stopwords.words('english'))
    query_tokens = [word for word in word_tokenize(query.lower()) if word.isalnum() and word not in stop_words]

    # Generate synonyms for query tokens
    synonyms = set()
    for token in query_tokens:
        for syn in wordnet.synsets(token):
            for lemma in syn.lemmas():
                synonyms.add(lemma.name().lower())
    query_tokens.extend(synonyms)

    # Initialize score
    score = 0

    # Check matches for the entire query as a phrase
    if query in topic.lower():
        score += phrase_weight
    if query in subtopic_name.lower():
        score += phrase_weight
    if query in description.lower():
        score += phrase_weight

    # Fuzzy match for the entire query
    score += fuzz.partial_ratio(query, topic) * topic_weight / 100
    score += fuzz.partial_ratio(query, subtopic_name) * subtopic_weight / 100
    score += fuzz.partial_ratio(query, description) * description_weight / 100

    # Check matches in file content
    if file_path and os.path.exists(file_path):
        with open(file_path, "r") as file:
            file_content = file.read().lower()
            if query in file_content:
                score += file_weight * file_content.count(query)
            for token in query_tokens:
                if token in file_content:
                    score += file_weight * file_content.count(token)

    return score


if __name__ == "__main__":
    app.run(debug=True)
