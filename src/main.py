import asyncio
import time
import os
import zipfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from common_code.config import get_settings
from common_code.http_client import HttpClient
from common_code.logger.logger import get_logger, Logger
from common_code.service.controller import router as service_router
from common_code.service.service import ServiceService
from common_code.storage.service import StorageService
from common_code.tasks.controller import router as tasks_router
from common_code.tasks.service import TasksService
from common_code.tasks.models import TaskData
from common_code.service.models import Service
from common_code.service.enums import ServiceStatus
from common_code.common.models import FieldDescription, ExecutionUnitTag, TestResultList
from common_code.common.enums import (
    FieldDescriptionType,
    ExecutionUnitTagName,
    ExecutionUnitTagAcronym,
)
from contextlib import asynccontextmanager

#TODO: check this with other devs
import sys

sys.path.append('../tests/')

import test_processing

# Imports required by the service's model
import json
import cv2
import numpy as np

settings = get_settings()


class MyService(Service):
    """
    Average shade service model
    """

    # Any additional fields must be excluded of model by adding a leading underscore for Pydantic to work
    _model: object
    _logger: Logger

    def __init__(self):
        super().__init__(
            name="Average Shade",
            slug="average-shade",
            url=settings.service_url,
            summary=api_summary,
            description=api_description,
            status=ServiceStatus.AVAILABLE,
            data_in_fields=[
                FieldDescription(
                    name="image",
                    type=[
                        FieldDescriptionType.IMAGE_PNG,
                        FieldDescriptionType.IMAGE_JPEG,
                    ],
                ),
            ],
            data_out_fields=[
                FieldDescription(
                    name="result", type=[FieldDescriptionType.APPLICATION_JSON]
                ),
            ],
            tags=[
                ExecutionUnitTag(
                    name=ExecutionUnitTagName.IMAGE_PROCESSING,
                    acronym=ExecutionUnitTagAcronym.IMAGE_PROCESSING,
                ),
            ],
            docs_url="https://docs.swiss-ai-center.ch/reference/services/average-shade/",
            has_ai=False,
        )
        self._logger = get_logger(settings)

    def process(self, data):
        # Get raw image data
        raw = data["image"].data
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        average_color_row = np.average(img, axis=0)
        average_color = np.average(average_color_row, axis=0)
        return {
            "result": TaskData(
                data=json.dumps(
                    {
                        "Red": int(average_color[2]),
                        "Green": int(average_color[1]),
                        "Blue": int(average_color[0]),
                    }
                ),
                type=FieldDescriptionType.APPLICATION_JSON,
            )
        }

    def main_test(self):
        results = [test_processing.test_image_1(self), test_processing.test_image_2(self)]
        tests_passed = all([result["result"] for result in results])
        return TestResultList(results=results, tests_passed=tests_passed)




service_service: ServiceService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Manual instances because startup events doesn't support Dependency Injection
    # https://github.com/tiangolo/fastapi/issues/2057
    # https://github.com/tiangolo/fastapi/issues/425

    # Global variable
    global service_service

    # Startup
    logger = get_logger(settings)
    http_client = HttpClient()
    storage_service = StorageService(logger)
    my_service = MyService()
    tasks_service = TasksService(logger, settings, http_client, storage_service)
    service_service = ServiceService(logger, settings, http_client, tasks_service)

    tasks_service.set_service(my_service)

    # Start the tasks service
    tasks_service.start()

    async def announce():
        retries = settings.engine_announce_retries
        for engine_url in settings.engine_urls:
            announced = False
            while not announced and retries > 0:
                announced = await service_service.announce_service(
                    my_service, engine_url
                )
                retries -= 1
                if not announced:
                    time.sleep(settings.engine_announce_retry_delay)
                    if retries == 0:
                        logger.warning(
                            f"Aborting service announcement after "
                            f"{settings.engine_announce_retries} retries"
                        )

    # Announce the service to its engine
    asyncio.ensure_future(announce())

    yield

    # Shutdown
    for engine_url in settings.engine_urls:
        await service_service.graceful_shutdown(my_service, engine_url)


api_description = """
Returns the average shade of an image.
"""
api_summary = """
Returns the average shade of an image.
"""

# Define the FastAPI application with information
app = FastAPI(
    lifespan=lifespan,
    title="Average Shade API.",
    description=api_description,
    version="1.0.0",
    contact={
        "name": "Swiss AI Center",
        "url": "https://swiss-ai-center.ch/",
        "email": "info@swiss-ai-center.ch",
    },
    swagger_ui_parameters={
        "tagsSorter": "alpha",
        "operationsSorter": "method",
    },
    license_info={
        "name": "GNU Affero General Public License v3.0 (GNU AGPLv3)",
        "url": "https://choosealicense.com/licenses/agpl-3.0/",
    },
)

# Include routers from other files
app.include_router(service_router, tags=["Service"])
app.include_router(tasks_router, tags=["Tasks"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs", status_code=301)


#TODO: check what group this endpoint should be in

@app.get(
    "/test",
    summary="Tests the service",
    responses={
        200: {"detail": "Tests failed"},
        204: {"detail": "Tests passed"},
        500: {"detail": "Internal Server error"},
    },
    status_code=204,
)
async def test():
    my_service = MyService()
    loop = asyncio.get_event_loop()
    test_result_future = loop.run_in_executor(None, my_service.main_test)
    test_result_list = await test_result_future
    if not test_result_list["tests_passed"]:
        raise HTTPException(status_code=200, detail=test_result_list["results"])


@app.get(
    "/download_test_data/",
    summary="Download test data",
    responses={
        200: {"detail": "Test data downloaded"},
        500: {"detail": "Internal Server error"},
        404: {"detail": "Data not found"},
    },
    status_code=200,
)
async def download_test_data():
    folder_path = os.path.join(".", "test_data")
    zip_file_path = os.path.join(".", "test_data", "test_data.zip")

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Data not found")

    if not os.path.exists(zip_file_path):
        with zipfile.ZipFile(zip_file_path, "w") as zip_file:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path) and file_name.lower().endswith(".jpg"):
                    zip_file.write(file_path, file_name)

    return FileResponse(
        zip_file_path, media_type="application/octet-stream", filename="test_data.zip"
    )
