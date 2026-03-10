from common_code.config import get_settings
from common_code.logger.logger import get_logger, Logger
from common_code.service.models import Service
from common_code.service.enums import ServiceStatus
from common_code.common.enums import FieldDescriptionType, ExecutionUnitTagName, ExecutionUnitTagAcronym
from common_code.common.models import FieldDescription, ExecutionUnitTag
from common_code.tasks.models import TaskData

# Imports required by the service's model
import json
import cv2
import numpy as np

settings = get_settings()

api_description = """
Returns the average shade of an image.
"""
api_summary = """
Returns the average shade of an image.
"""
api_title = "Average Shade API."
version = "1.0.0"

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
                FieldDescription(name="image", type=[FieldDescriptionType.IMAGE_PNG, FieldDescriptionType.IMAGE_JPEG]),
            ],
            data_out_fields=[
                FieldDescription(name="result", type=[FieldDescriptionType.APPLICATION_JSON]),
            ],
            tags=[
                ExecutionUnitTag(
                    name=ExecutionUnitTagName.IMAGE_PROCESSING,
                    acronym=ExecutionUnitTagAcronym.IMAGE_PROCESSING
                ),
            ],
            docs_url="https://docs.swiss-ai-center.ch/reference/services/average-shade/",
            has_ai=False
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
                data=json.dumps({
                    "Red": int(average_color[2]),
                    "Green": int(average_color[1]),
                    "Blue": int(average_color[0])
                }).encode("utf-8"),
                type=FieldDescriptionType.APPLICATION_JSON
            )
        }
