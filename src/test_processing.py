from typing import List
from typing_extensions import TypedDict
import os
import json
import requests


class TestResult(TypedDict):
    name: str
    result: bool


class TestResultList(TypedDict):
    results: List[TestResult]


def main_test():
    result1 = test_image_1()
    result2 = test_image_2()

    return TestResultList(results=[result1, result2])


def test_image_1():
    image_path = os.path.join("..", "data", "pexels-fanny-hagan.jpg")
    expected_results_path = os.path.join(
        "..", "data", "results-pexels-fanny-hagan.json"
    )

    with open(expected_results_path, "r") as f:
        expected_results = json.load(f)

    with open(image_path, "rb") as f:
        image_data = f.read()

    # Send the image as an HTTP object
    response = requests.post(url="0.0.0.0:80/process", data=image_data)
    actual_results = response.json()
    print(actual_results)

    return TestResult(
        name="test_image_1", result=actual_results.data == expected_results
    )


def test_image_2():
    image_path = os.path.join("..", "data", "pexels-gosia-k.jpg")
    expected_results_path = os.path.join("..", "data", "results-pexels-gosia-k.json")

    with open(expected_results_path, "r") as f:
        expected_results = json.load(f)

    with open(image_path, "rb") as f:
        image_data = f.read()

    # FIXME: requests.exceptions.InvalidSchema: No connection adapters were found for 'localhost:80/process'
    response = requests.post(url="localhost:80/process", data=image_data)
    actual_results = response.json()
    print(actual_results)

    return TestResult(
        name="test_image_2", result=actual_results.data == expected_results
    )
