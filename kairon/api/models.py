from typing import List, Any, Dict, Optional

import validators
from fastapi.param_functions import Form
from fastapi.security import OAuth2PasswordRequestForm

from kairon.exceptions import AppException
from kairon.shared.data.constant import EVENT_STATUS, SLOT_MAPPING_TYPE, SLOT_TYPE, ACCESS_ROLES, ACTIVITY_STATUS, \
    INTEGRATION_STATUS, FALLBACK_MESSAGE, DEFAULT_NLU_FALLBACK_RESPONSE
from ..shared.actions.models import ActionParameterType, EvaluationType, DispatchType, DbQueryValueType, \
    DbActionOperationType
from ..shared.constants import SLOT_SET_TYPE, FORM_SLOT_SET_TYPE

ValidationFailure = validators.ValidationFailure
from pydantic import BaseModel, validator, SecretStr, root_validator, constr
from ..shared.models import StoryStepType, StoryType, TemplateType, HttpContentType, LlmPromptSource, LlmPromptType, \
    CognitionDataType, CognitionMetadataType


class RecaptchaVerifiedRequest(BaseModel):
    recaptcha_response: str = None
    remote_ip: str = None

    @root_validator
    def validate_recaptcha(cls, values):
        from kairon.shared.utils import Utility

        secret = Utility.environment['security'].get('recaptcha_secret', None)
        if Utility.environment['security']['validate_recaptcha'] and not Utility.check_empty_string(secret):
            Utility.validate_recaptcha(values.get('recaptcha_response'), values.get('remote_ip'))
        return values


class RecaptchaVerifiedOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    """
    Dependency class overridden from OAuth2PasswordRequestForm.
    """

    def __init__(
            self,
            grant_type: str = Form(None, regex="password"),
            username: str = Form(...),
            password: str = Form(...),
            scope: str = Form(""),
            client_id: Optional[str] = Form(None),
            client_secret: Optional[str] = Form(None),
            recaptcha_response: str = Form(None),
            remote_ip: str = Form(None),
            fingerprint: str = Form(None)
    ):
        """
        @param grant_type: the OAuth2 spec says it is required and MUST be the fixed string "password".
        Nevertheless, this dependency class is permissive and allows not passing it. If you want to enforce it,
        use instead the OAuth2PasswordRequestFormStrict dependency.
        @param username: username string. The OAuth2 spec requires the exact field name "username".
        @param password: password string. The OAuth2 spec requires the exact field name "password".
        @param scope: Optional string. Several scopes (each one a string) separated by spaces.
        E.g. "items:read items:write users:read profile openid"
        @param client_id: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
        @param client_secret: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
        @param recaptcha_response: optional string. recaptcha response.
        @param remote_ip: optional string.  remote ip address.
        @param fingerprint: optional string. device fingerprint.
        """
        from kairon.shared.utils import Utility

        secret = Utility.environment['security'].get('recaptcha_secret', None)
        if Utility.environment['security']['validate_recaptcha'] and not Utility.check_empty_string(secret):
            Utility.validate_recaptcha(recaptcha_response, remote_ip)
        OAuth2PasswordRequestForm.__init__(self, grant_type, username, password, scope, client_id, client_secret)
        self.recaptcha_response = recaptcha_response
        self.remote_ip = remote_ip
        if Utility.environment["user"]["validate_trusted_device"] and Utility.check_empty_string(fingerprint):
            raise AppException("fingerprint is required")
        self.fingerprint = fingerprint


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class Response(BaseModel):
    success: bool = True
    message: Any = None
    data: Any
    error_code: int = 0


class RequestData(BaseModel):
    data: Any


class TextData(BaseModel):
    data: str


class RecaptchaVerifiedTextData(RecaptchaVerifiedRequest):
    data: str


class TextDataLowerCase(BaseModel):
    data: constr(to_lower=True, strip_whitespace=True)


class ListData(BaseModel):
    data: List[str]


class RegisterAccount(RecaptchaVerifiedRequest):
    email: constr(to_lower=True, strip_whitespace=True)
    first_name: str
    last_name: str
    password: SecretStr
    confirm_password: SecretStr
    account: str
    fingerprint: str = None

    @validator("email")
    def validate_email(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility
        try:
            Utility.verify_email(v)
        except AppException as e:
            raise ValueError(str(e))
        return v

    @validator("password")
    def validate_password(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        try:
            Utility.valid_password(v.get_secret_value())
        except AppException as e:
            raise ValueError(str(e))
        return v

    @validator("confirm_password")
    def validate_confirm_password(cls, v, values, **kwargs):
        if (
                "password" in values
                and v.get_secret_value() != values["password"].get_secret_value()
        ):
            raise ValueError("Password and Confirm Password does not match")
        return v

    @root_validator
    def validate_fingerprint(cls, values):
        from kairon.shared.utils import Utility

        if Utility.environment['user']['validate_trusted_device'] and Utility.check_empty_string(
                values.get('fingerprint')):
            raise ValueError("fingerprint is required")
        return values


class BotAccessRequest(RecaptchaVerifiedRequest):
    email: constr(to_lower=True, strip_whitespace=True)
    role: ACCESS_ROLES = ACCESS_ROLES.TESTER.value
    activity_status: ACTIVITY_STATUS = ACTIVITY_STATUS.INACTIVE.value

    @validator("email")
    def validate_email(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility
        try:
            Utility.verify_email(v)
        except AppException as e:
            raise ValueError(str(e))
        return v

    @validator("role")
    def validate_role(cls, v, values, **kwargs):
        if v == ACCESS_ROLES.OWNER.value:
            raise ValueError("There can be only 1 owner per bot")
        return v


class EndPointBot(BaseModel):
    url: str
    token: str = None
    token_type: str = None


class EndPointAction(BaseModel):
    url: str


class EndPointHistory(BaseModel):
    url: str
    token: str = None


class Endpoint(BaseModel):
    bot_endpoint: EndPointBot = None
    action_endpoint: EndPointAction = None
    history_endpoint: EndPointHistory = None


class RasaConfig(BaseModel):
    language: str = "en"
    pipeline: List[Dict]
    policies: List[Dict]


class ComponentConfig(BaseModel):
    nlu_epochs: int = None
    response_epochs: int = None
    ted_epochs: int = None
    nlu_confidence_threshold: float = None
    action_fallback: str = None
    action_fallback_threshold: float = None

    @validator('nlu_epochs', 'response_epochs', 'ted_epochs')
    def validate_epochs(cls, v):
        from kairon.shared.utils import Utility

        if v is not None and v < 1:
            raise ValueError("Choose a positive number as epochs")
        elif v > Utility.environment['model']['config_properties']['epoch_max_limit']:
            epoch_max_limit = Utility.environment['model']['config_properties']['epoch_max_limit']
            raise ValueError(f"Please choose a epoch between 1 and {epoch_max_limit}")
        return v

    @validator("nlu_confidence_threshold", "action_fallback_threshold")
    def validate_confidence_threshold(cls, v):
        if v is not None and (v < 0.3 or v > 0.9):
            raise ValueError("Please choose a threshold between 0.3 and 0.9")
        return v


class Password(RecaptchaVerifiedRequest):
    data: str
    password: SecretStr
    confirm_password: SecretStr

    @validator("password")
    def validate_password(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        try:
            Utility.valid_password(v.get_secret_value())
        except AppException as e:
            raise ValueError(str(e))
        return v

    @validator("confirm_password")
    def validate_confirm_password(cls, v, values, **kwargs):
        if (
                "password" in values
                and v.get_secret_value() != values["password"].get_secret_value()
        ):
            raise ValueError("Password and Confirm Password does not match")
        return v


class HttpActionParameters(BaseModel):
    key: str
    value: str = None
    parameter_type: ActionParameterType
    encrypt: bool = False

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(values.get('key')):
            raise ValueError("key cannot be empty")

        if values.get('parameter_type') == ActionParameterType.slot and Utility.check_empty_string(values.get('value')):
            raise ValueError("Provide name of the slot as value")

        if values.get('parameter_type') == ActionParameterType.key_vault and Utility.check_empty_string(
                values.get('value')):
            raise ValueError("Provide key from key vault as value")

        if values.get('parameter_type') == ActionParameterType.key_vault:
            values['encrypt'] = True

        return values


class SetSlotsUsingActionResponse(BaseModel):
    name: str
    value: str
    evaluation_type: EvaluationType = EvaluationType.expression

    @validator("name")
    def validate_name(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(v):
            raise ValueError("slot name is required")
        return v

    @validator("value")
    def validate_expression(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(v):
            raise ValueError("expression is required to evaluate value of slot")
        return v


class ActionResponseEvaluation(BaseModel):
    value: str = None
    dispatch: bool = True
    evaluation_type: EvaluationType = EvaluationType.expression
    dispatch_type: DispatchType = DispatchType.text.value

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        if values.get('dispatch') is True and Utility.check_empty_string(values.get('value')):
            raise ValueError("response is required for dispatch")

        return values


class HttpActionConfigRequest(BaseModel):
    action_name: constr(to_lower=True, strip_whitespace=True)
    content_type: HttpContentType = HttpContentType.application_json
    response: ActionResponseEvaluation = None
    http_url: str
    request_method: str
    params_list: List[HttpActionParameters] = []
    dynamic_params: str = None
    headers: List[HttpActionParameters] = []
    set_slots: List[SetSlotsUsingActionResponse] = []

    @validator("action_name")
    def validate_action_name(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(v):
            raise ValueError("action_name is required")
        return v

    @validator("http_url")
    def validate_http_url(cls, v, values, **kwargs):
        if isinstance(validators.url(v), ValidationFailure):
            raise ValueError("URL is malformed")
        return v

    @validator("request_method")
    def validate_request_method(cls, v, values, **kwargs):
        if v.upper() not in ("GET", "POST", "PUT", "DELETE"):
            raise ValueError("Invalid HTTP method")
        return v.upper()


class QueryConfig(BaseModel):
    type: DbQueryValueType
    value: DbActionOperationType

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(values.get('type')):
            raise ValueError("type cannot be empty")

        if Utility.check_empty_string(values.get('value')):
            raise ValueError("value cannot be empty")

        return values


class PayloadConfig(BaseModel):
    type: DbQueryValueType
    value: Any

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(values.get('type')):
            raise ValueError("type is required")

        if not values.get('value') or values.get('value') is None:
            raise ValueError("value is required")

        return values


class DatabaseActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    query: QueryConfig
    payload: PayloadConfig
    response: ActionResponseEvaluation = None
    set_slots: List[SetSlotsUsingActionResponse] = []

    @validator("name")
    def validate_action_name(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(v):
            raise ValueError("name is required")
        return v


class TrainingData(BaseModel):
    intent: constr(to_lower=True, strip_whitespace=True)
    training_examples: List[str]
    response: str


class BulkTrainingDataAddRequest(BaseModel):
    history_id: str
    training_data: List[TrainingData]


class TrainingDataGeneratorResponseModel(BaseModel):
    intent: str
    training_examples: List[str]
    response: str


class TrainingDataGeneratorStatusModel(BaseModel):
    status: EVENT_STATUS
    response: List[TrainingData] = None
    exception: str = None


class StoryStepRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True) = None
    type: StoryStepType
    value: Any = None


class MultiStoryStepRequest(StoryStepRequest):
    node_id: str
    component_id: str


class StoryStepData(BaseModel):
    step: MultiStoryStepRequest
    connections: List[MultiStoryStepRequest] = None


class StoryMetadata(BaseModel):
    node_id: str
    flow_type: StoryType = StoryType.story.value


class MultiFlowStoryRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    steps: List[StoryStepData]
    metadata: List[StoryMetadata] = None

    @validator("steps")
    def validate_request_method(cls, v, values, **kwargs):
        if not v:
            raise ValueError("Steps are required to form Flow")
        return v


class StoryRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    type: StoryType
    steps: List[StoryStepRequest]
    template_type: TemplateType = None

    class Config:
        use_enum_values = True

    def get_steps(self):
        return [step.dict() for step in self.steps]

    @validator("steps")
    def validate_request_method(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if not v:
            raise ValueError("Steps are required to form Flow")

        if v[0].type != StoryStepType.intent:
            raise ValueError("First step should be an intent")

        if v[len(v) - 1].type == StoryStepType.intent:
            raise ValueError("Intent should be followed by utterance or action")

        intents = 0
        for i, j in enumerate(range(1, len(v))):
            if v[i].type == StoryStepType.intent:
                intents = intents + 1
            if v[i].type == StoryStepType.intent and v[j].type == StoryStepType.intent:
                raise ValueError("Found 2 consecutive intents")
            if Utility.check_empty_string(v[i].name) and v[i].type != StoryStepType.form_end:
                raise ValueError(f"Only {StoryStepType.form_end} step type can have empty name")
        if 'type' in values:
            if values['type'] == StoryType.rule and intents > 1:
                raise ValueError(
                    f"""Found rules '{values['name']}' that contain more than intent.\nPlease use stories for this case""")
        return v


class FeedbackRequest(BaseModel):
    rating: float
    scale: float = 5
    feedback: str = None


class GPTRequest(BaseModel):
    api_key: str
    data: List[str]
    engine: str = "davinci"
    temperature: float = 0.75
    max_tokens: int = 100
    num_responses: int = 10

    @validator("data")
    def validate_gpt_questions(cls, v, values, **kwargs):
        if len(v) <= 0:
            raise ValueError("Question Please!")
        elif len(v) > 5:
            raise ValueError("Max 5 Questions are allowed!")
        return v


class ParaphrasesRequest(BaseModel):
    data: List[str]

    @validator("data")
    def validate_paraphrases_questions(cls, v, values, **kwargs):
        if len(v) <= 0:
            raise ValueError("Question Please!")
        elif len(v) > 5:
            raise ValueError("Max 5 Questions are allowed!")
        return v


class SlotRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    type: SLOT_TYPE
    initial_value: Any = None
    auto_fill: bool = True
    values: List[str] = None
    max_value: float = None
    min_value: float = None
    influence_conversation: bool = False


class SynonymRequest(BaseModel):
    value: List[str]

    @validator("value")
    def validate_value(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility
        if len(v) <= 0:
            raise ValueError("value field cannot be empty")
        for ele in v:
            if Utility.check_empty_string(ele):
                raise ValueError("value cannot be an empty string")
        return v


class DictData(BaseModel):
    data: dict


class RecaptchaVerifiedDictData(DictData):
    recaptcha_response: str = None


class RegexRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    pattern: str

    @validator("name")
    def validate_name(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility
        if Utility.check_empty_string(v):
            raise ValueError("Regex name cannot be empty or a blank space")
        return v

    @validator("pattern")
    def validate_pattern(cls, f, values, **kwargs):
        from kairon.shared.utils import Utility
        import re
        if Utility.check_empty_string(f):
            raise ValueError("Regex pattern cannot be empty or a blank space")
        try:
            re.compile(f)
        except Exception:
            raise AppException("invalid regular expression")
        return f


class LookupTablesRequest(BaseModel):
    value: List[str]

    @validator("value")
    def validate_value(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility
        if len(v) <= 0:
            raise ValueError("value field cannot be empty")
        for ele in v:
            if Utility.check_empty_string(ele):
                raise ValueError("lookup value cannot be empty or a blank space")
        return v


class SlotMapping(BaseModel):
    entity: constr(to_lower=True, strip_whitespace=True) = None
    type: SLOT_MAPPING_TYPE
    value: Any = None
    intent: List[constr(to_lower=True, strip_whitespace=True)] = None
    not_intent: List[constr(to_lower=True, strip_whitespace=True)] = None


class SlotMappingRequest(BaseModel):
    slot: constr(to_lower=True, strip_whitespace=True)
    mapping: List[SlotMapping]

    @validator("mapping")
    def validate_mapping(cls, v, values, **kwargs):
        if not v or v == [{}]:
            raise ValueError("At least one mapping is required")
        return v


class FormSlotSetModel(BaseModel):
    type: FORM_SLOT_SET_TYPE = FORM_SLOT_SET_TYPE.current.value
    value: Any = None


class FormSettings(BaseModel):
    ask_questions: List[str]
    slot: str
    is_required: bool = True
    validation_semantic: str = None
    valid_response: str = None
    invalid_response: str = None
    slot_set: FormSlotSetModel = FormSlotSetModel()

    @validator("ask_questions")
    def validate_responses(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility
        err_msg = "Questions cannot be empty or contain spaces"
        if not v:
            raise ValueError(err_msg)

        for response in v:
            if Utility.check_empty_string(response):
                raise ValueError(err_msg)
        return v

    @validator("slot")
    def validate_slot(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if Utility.check_empty_string(v):
            raise ValueError("Slot is required")
        return v


class Forms(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    settings: List[FormSettings]


class SetSlots(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    type: SLOT_SET_TYPE
    value: Any = None


class SlotSetActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    set_slots: List[SetSlots]


class CustomActionParameter(BaseModel):
    value: str = None
    parameter_type: ActionParameterType = ActionParameterType.value

    @validator("parameter_type")
    def validate_parameter_type(cls, v, values, **kwargs):
        allowed_values = {ActionParameterType.value, ActionParameterType.slot, ActionParameterType.key_vault,
                          ActionParameterType.sender_id}
        if v not in allowed_values:
            raise ValueError(f"Invalid parameter type. Allowed values: {allowed_values}")
        return v

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        if values.get('parameter_type') == ActionParameterType.slot and Utility.check_empty_string(values.get('value')):
            raise ValueError("Provide name of the slot as value")

        if values.get('parameter_type') == ActionParameterType.key_vault and Utility.check_empty_string(
                values.get('value')):
            raise ValueError("Provide key from key vault as value")

        return values


class GoogleSearchActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    api_key: CustomActionParameter
    search_engine_id: str
    failure_response: str = 'I have failed to process your request.'
    num_results: int = 1
    dispatch_response: bool = True
    set_slot: str = None

    @validator("num_results")
    def validate_num_results(cls, v, values, **kwargs):
        if not v or v < 1:
            raise ValueError("num_results must be greater than or equal to 1!")
        return v


class EmailActionRequest(BaseModel):
    action_name: constr(to_lower=True, strip_whitespace=True)
    smtp_url: str
    smtp_port: int
    smtp_userid: CustomActionParameter = None
    smtp_password: CustomActionParameter
    from_email: str
    subject: str
    to_email: List[str]
    response: str
    tls: bool = False


class JiraActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    url: str
    user_name: str
    api_token: CustomActionParameter
    project_key: str
    issue_type: str
    parent_key: str = None
    summary: str
    response: str


class ZendeskActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    subdomain: str
    user_name: str
    api_token: CustomActionParameter
    subject: str
    response: str


class PipedriveActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    domain: str
    api_token: CustomActionParameter
    title: str
    response: str
    metadata: dict

    @validator("metadata")
    def validate_metadata(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if not v or Utility.check_empty_string(v.get('name')):
            raise ValueError("name is required")
        return v


class HubspotFormsActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    portal_id: str
    form_guid: str
    fields: List[HttpActionParameters]
    response: str


class QuickReplies(BaseModel):
    text: str
    payload: str
    message: str = None
    is_dynamic_msg: bool = False


class TwoStageFallbackTextualRecommendations(BaseModel):
    count: int = 0
    use_intent_ranking: bool = False


class TwoStageFallbackConfigRequest(BaseModel):
    fallback_message: str = FALLBACK_MESSAGE
    text_recommendations: TwoStageFallbackTextualRecommendations = None
    trigger_rules: List[QuickReplies] = None

    @root_validator
    def check(cls, values):
        if not values.get('text_recommendations') and not values['trigger_rules']:
            raise ValueError("One of text_recommendations or trigger_rules should be defined")
        if values.get('text_recommendations') and values['text_recommendations'].count < 0:
            raise ValueError("count cannot be negative")
        return values


class LlmPromptRequest(BaseModel):
    name: str
    data: str = None
    instructions: str = None
    type: LlmPromptType
    source: LlmPromptSource
    is_enabled: bool = True


class PromptActionConfigRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    num_bot_responses: int = 5
    failure_message: str = DEFAULT_NLU_FALLBACK_RESPONSE
    top_results: int = 10
    similarity_threshold: float = 0.70
    enable_response_cache: bool = False
    hyperparameters: dict = None
    llm_prompts: List[LlmPromptRequest]
    set_slots: List[SetSlotsUsingActionResponse] = []
    dispatch_response: bool = True

    @validator("similarity_threshold")
    def validate_similarity_threshold(cls, v, values, **kwargs):
        if not 0.3 <= v <= 1:
            raise ValueError("similarity_threshold should be within 0.3 and 1")
        return v

    @validator("llm_prompts")
    def validate_llm_prompts(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        Utility.validate_kairon_faq_llm_prompts([vars(value) for value in v], ValueError)
        return v

    @validator("top_results")
    def validate_top_results(cls, v, values, **kwargs):
        if v > 30:
            raise ValueError("top_results should not be greater than 30")
        return v

    @validator("num_bot_responses")
    def validate_num_bot_responses(cls, v, values, **kwargs):
        if v > 5:
            raise ValueError("num_bot_responses should not be greater than 5")
        return v

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        if not values.get('hyperparameters'):
            values['hyperparameters'] = {}

        for key, value in Utility.get_llm_hyperparameters().items():
            if key not in values['hyperparameters']:
                values['hyperparameters'][key] = value
        return values


class Metadata(BaseModel):
    column_name: str
    data_type: CognitionMetadataType
    enable_search: bool = True
    create_embeddings: bool = True


class CognitiveDataRequest(BaseModel):
    data: Any
    content_type: CognitionDataType
    metadata: List[Metadata] = None

    @root_validator
    def check(cls, values):
        from kairon.shared.utils import Utility

        data = values.get("data")
        metadata = values.get("metadata", [])
        for metadata_item in metadata:
            Utility.retrieve_data(data, metadata_item.dict())
        return values


class RazorpayActionRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    api_key: CustomActionParameter
    api_secret: CustomActionParameter
    amount: CustomActionParameter
    currency: CustomActionParameter
    username: CustomActionParameter = None
    email: CustomActionParameter = None
    contact: CustomActionParameter = None


class IntegrationRequest(BaseModel):
    name: constr(to_lower=True, strip_whitespace=True)
    expiry_minutes: int = 0
    access_list: list = None
    role: ACCESS_ROLES = ACCESS_ROLES.CHAT.value
    status: INTEGRATION_STATUS = INTEGRATION_STATUS.ACTIVE.value


class KeyVaultRequest(BaseModel):
    key: str
    value: str

    @validator("key")
    def validate_key(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if not v or Utility.check_empty_string(v):
            raise ValueError("key is required")
        return v

    @validator("value")
    def validate_value(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if not v or Utility.check_empty_string(v):
            raise ValueError("value is required")
        return v


class EventConfig(BaseModel):
    ws_url: str
    headers: dict
    method: str

    @validator("ws_url")
    def validate_ws_url(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if not v or Utility.check_empty_string(v):
            raise ValueError("url can not be empty")
        return v

    @validator("headers")
    def validate_headers(cls, v, values, **kwargs):
        if not v or len(v) < 1:
            v = {}
        return v


class IDPConfig(BaseModel):
    config: dict
    organization: str

    @validator("config")
    def validate_config(cls, v, values, **kwargs):
        if not v or len(v) == 0:
            v = {}
        return v

    @validator("organization")
    def validate_organization(cls, v, values, **kwargs):
        from kairon.shared.utils import Utility

        if not v or Utility.check_empty_string(v):
            raise ValueError("Organization can not be empty")
        return v
