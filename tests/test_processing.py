import os
import json
from common_code.service.models import Service
from common_code.tasks.models import TaskData
from common_code.common.models import TestResult, TestResultList


def test_image_1(service: Service):
    image_path = os.path.join("test_data", "pexels-fanny-hagan.jpg")
    expected_results_path = os.path.join("test_data", "results-pexels-fanny-hagan.json")

    with open(expected_results_path, "r") as f:
        expected_results = json.load(f)

    with open(image_path, "rb") as f:
        image_data = f.read()

    data = {"image": TaskData(data=image_data, type="image/jpeg")}
    response = service.process(data)
    actual_results = json.loads(response["result"].data.decode("utf-8"))

    return TestResult(name="test_image_1", result=actual_results == expected_results)


def test_image_2(service: Service):
    image_path = os.path.join("test_data", "pexels-gosia-k.jpg")
    expected_results_path = os.path.join("test_data", "results-pexels-gosia-k.json")

    with open(expected_results_path, "r") as f:
        expected_results = json.load(f)

    with open(image_path, "rb") as f:
        image_data = f.read()

    data = {"image": TaskData(data=image_data, type="image/jpeg")}
    response = service.process(data)
    actual_results = json.loads(response["result"].data.decode("utf-8"))

    return TestResult(name="test_image_2", result=actual_results == expected_results)
