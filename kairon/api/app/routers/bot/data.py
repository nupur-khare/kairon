import os

from fastapi import UploadFile, File, Security, APIRouter
from starlette.requests import Request
from starlette.responses import FileResponse

from kairon.api.models import Response, TextData, CognitiveDataRequest, CognitionSchemaRequest
from kairon.events.definitions.faq_importer import FaqDataImporterEvent
from kairon.shared.auth import Authentication
from kairon.shared.cognition.processor import CognitionDataProcessor
from kairon.shared.constants import DESIGNER_ACCESS
from kairon.shared.data.processor import MongoProcessor
from kairon.shared.models import User
from kairon.shared.utils import Utility

router = APIRouter()
processor = MongoProcessor()
cognition_processor = CognitionDataProcessor()


@router.post("/faq/upload", response_model=Response)
def upload_faq_files(
        csv_file: UploadFile = File(...),
        overwrite: bool = True,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Uploads faq csv/excel file
    """
    event = FaqDataImporterEvent(
        current_user.get_bot(), current_user.get_user(), overwrite=overwrite
    )
    event.validate(training_data_file=csv_file)
    event.enqueue()
    return {"message": "Upload in progress! Check logs."}


@router.get("/faq/download", response_model=Response)
async def download_faq_files(
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Downloads faq into csv file
    """
    qna = list(processor.flatten_qna(bot=current_user.get_bot(), fetch_all=True))
    file, _ = Utility.download_csv(qna, filename="faq.csv")
    response = FileResponse(
        file, filename=os.path.basename(file)
    )
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=" + os.path.basename(file)
    return response


@router.post("/text/faq", response_model=Response)
async def save_bot_text(
        text: TextData,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
        collection: str = None
):
    """
    Saves text content into the bot
    """
    return {
        "message": "Text saved!",
        "data": {
            "_id": cognition_processor.save_content(
                    text.data,
                    current_user.get_user(),
                    current_user.get_bot(),
                    collection
            )
        }
    }


@router.put("/text/faq/{text_id}", response_model=Response)
async def update_bot_text(
        text_id: str,
        text: TextData,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
        collection: str = None,
):
    """
    Updates text content into the bot
    """
    return {
        "message": "Text updated!",
        "data": {
            "_id": cognition_processor.update_content(
                text_id,
                text.data,
                current_user.get_user(),
                current_user.get_bot(),
                collection
            )
        }
    }


@router.delete("/text/faq/{text_id}", response_model=Response)
async def delete_bot_text(
        text_id: str,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Deletes text content of the bot
    """
    cognition_processor.delete_content(text_id, current_user.get_user(), current_user.get_bot())
    return {
        "message": "Text deleted!"
    }


@router.get("/text/faq", response_model=Response)
async def get_text(
        request: Request,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Fetches text content of the bot
    """
    kwargs = request.query_params._dict.copy()
    return {"data": list(cognition_processor.get_content(current_user.get_bot(), **kwargs))}


@router.get("/text/faq/collection", response_model=Response)
async def list_collection(
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Fetches text content of the bot
    """
    return {"data": cognition_processor.list_cognition_collections(current_user.get_bot())}


@router.post("/cognition/schema", response_model=Response)
async def save_cognition_schema(
        metadata: CognitionSchemaRequest,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Saves and updates cognition metadata into the bot
    """
    return {
        "message": "Schema saved!",
        "data": {
            "_id": cognition_processor.save_cognition_schema(
                    metadata.dict(),
                    current_user.get_user(),
                    current_user.get_bot(),
            )
        }
    }


@router.put("/cognition/schema/{metadata_id}", response_model=Response)
async def update_cognition_schema(
        metadata_id: str,
        metadata: CognitionSchemaRequest,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Saves and updates cognition metadata into the bot
    """
    return {
        "message": "Schema updated!",
        "data": {
            "_id": cognition_processor.update_cognition_schema(
                    metadata_id,
                    metadata.dict(),
                    current_user.get_user(),
                    current_user.get_bot(),
            )
        }
    }


@router.delete("/cognition/schema/{metadata_id}", response_model=Response)
async def delete_cognition_schema(
        metadata_id: str,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Deletes cognition content of the bot
    """
    cognition_processor.delete_cognition_schema(metadata_id, current_user.get_bot())
    return {
        "message": "Schema deleted!"
    }


@router.get("/cognition/schema", response_model=Response)
async def list_cognition_schema(
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Fetches cognition content of the bot
    """
    return {"data": list(cognition_processor.list_cognition_schema(current_user.get_bot()))}


@router.post("/cognition", response_model=Response)
async def save_cognition_data(
        cognition: CognitiveDataRequest,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Saves cognition content into the bot
    """
    return {
        "message": "Record saved!",
        "data": {
            "_id": cognition_processor.save_cognition_data(
                    cognition.dict(),
                    current_user.get_user(),
                    current_user.get_bot(),
            )
        }
    }


@router.put("/cognition/{cognition_id}", response_model=Response)
async def update_cognition_data(
        cognition_id: str,
        cognition: CognitiveDataRequest,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Updates cognition content into the bot
    """
    return {
        "message": "Record updated!",
        "data": {
            "_id": cognition_processor.update_cognition_data(
                cognition_id,
                cognition.dict(),
                current_user.get_user(),
                current_user.get_bot(),
            )
        }
    }


@router.delete("/cognition/{cognition_id}", response_model=Response)
async def delete_cognition_data(
        cognition_id: str,
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Deletes cognition content of the bot
    """
    cognition_processor.delete_cognition_data(cognition_id, current_user.get_bot())
    return {
        "message": "Record deleted!"
    }


@router.get("/cognition", response_model=Response)
async def list_cognition_data(
        current_user: User = Security(Authentication.get_current_user_and_bot, scopes=DESIGNER_ACCESS),
):
    """
    Fetches cognition content of the bot
    """
    return {"data": list(cognition_processor.list_cognition_data(current_user.get_bot()))}
