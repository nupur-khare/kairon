import re

import pytest

from kairon.exceptions import AppException
from kairon.importer.validator.file_validator import TrainingDataValidator
from kairon.shared.data.constant import DEFAULT_NLU_FALLBACK_RESPONSE
from kairon.shared.utils import Utility


class TestTrainingDataValidator:

    def test_config_validation(self):
        config = Utility.load_yaml("./tests/testing_data/yml_training_files/config.yml")
        TrainingDataValidator.validate_rasa_config(config)

    def test_config_validation_invalid_pipeline(self):
        Utility.load_environment()
        config = Utility.load_yaml("./tests/testing_data/yml_training_files/config.yml")
        config.get('pipeline').append({'name': "XYZ"})
        error = TrainingDataValidator.validate_rasa_config(config)
        assert error[0] == "Invalid component XYZ"

    def test_config_validation_invalid_config(self):
        Utility.load_environment()
        config = Utility.load_yaml("./tests/testing_data/yml_training_files/config.yml")
        config.get('policies').append({'name': "XYZ"})
        error = TrainingDataValidator.validate_rasa_config(config)
        assert error[0] == "Invalid policy XYZ"

    @pytest.mark.asyncio
    async def test_validate_with_file_importer_invalid_yaml_format(self):
        # domain
        root = 'tests/testing_data/all'
        domain_path = 'tests/testing_data/validator/invalid_yaml/domain.yml'
        nlu_path = 'tests/testing_data/all/data'
        config_path = 'tests/testing_data/all/config.yml'
        with pytest.raises(AppException):
            await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)

        # config
        root = 'tests/testing_data/all'
        domain_path = 'tests/testing_data/all/domain.yml'
        nlu_path = 'tests/testing_data/all/data'
        config_path = 'tests/testing_data/validator/invalid_yaml/config.yml'
        with pytest.raises(AppException):
            await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)

        # nlu
        root = 'tests/testing_data/all'
        domain_path = 'tests/testing_data/all/domain.yml'
        nlu_path = 'tests/testing_data/validator/invalid_yaml/data'
        config_path = 'tests/testing_data/all/config.yml'
        with pytest.raises(AppException):
            await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)

        # stories
        root = 'tests/testing_data/all'
        domain_path = 'tests/testing_data/all/domain.yml'
        nlu_path = 'tests/testing_data/validator/invalid_yaml/data_2'
        config_path = 'tests/testing_data/all/config.yml'
        with pytest.raises(AppException):
            await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)

    @pytest.mark.asyncio
    async def test_validate_intent_mismatch(self):
        root = 'tests/testing_data/validator/intent_name_mismatch'
        domain_path = 'tests/testing_data/validator/intent_name_mismatch/domain.yml'
        nlu_path = 'tests/testing_data/validator/intent_name_mismatch/data'
        config_path = 'tests/testing_data/validator/intent_name_mismatch/config.yml'
        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        with pytest.raises(AppException):
            validator.validate_training_data()

        validator.validate_training_data(False)
        assert validator.summary['intents'][
                   0] == "The intent 'affirm' is listed in the domain file, but is not found in the NLU training data."
        assert validator.summary['intents'][
                   1] == "There is a message in the training data labeled with intent 'deny'. This intent is not listed in your domain."
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_empty_domain(self):
        root = 'tests/testing_data/validator/empty_domain'
        domain_path = 'tests/testing_data/validator/empty_domain/domain.yml'
        nlu_path = 'tests/testing_data/validator/valid/data'
        config_path = 'tests/testing_data/validator/valid/config.yml'
        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        with pytest.raises(AppException):
            validator.validate_training_data()

        validator.validate_training_data(False)
        assert validator.summary['intents']
        assert not validator.summary['utterances']
        assert validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert validator.summary['domain'] == ['domain.yml is empty!']
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_story_with_conflicts(self):
        root = 'tests/testing_data/validator/conflicting_stories'
        domain_path = 'tests/testing_data/validator/conflicting_stories/domain.yml'
        nlu_path = 'tests/testing_data/validator/conflicting_stories/data'
        config_path = 'tests/testing_data/validator/conflicting_stories/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert not validator.summary.get('intents')
        assert not validator.summary.get('utterances')
        assert validator.summary['stories'][
                   0] == "Story structure conflict after intent 'deny':\n  utter_goodbye predicted in 'deny'\n  utter_thanks predicted in 'refute'\n"
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_intent_in_story_not_in_domain(self):
        root = 'tests/testing_data/validator/intent_missing_in_domain'
        domain_path = 'tests/testing_data/validator/intent_missing_in_domain/domain.yml'
        nlu_path = 'tests/testing_data/validator/intent_missing_in_domain/data'
        config_path = 'tests/testing_data/validator/intent_missing_in_domain/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert validator.summary['intents'][
                   0] == 'There is a message in the training data labeled with intent \'deny\'. This intent is not listed in your domain.'
        assert validator.summary['intents'][
                   1] == 'The intent \'deny\' is used in your stories, but it is not listed in the domain file. You should add it to your domain file!'
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_intent_not_used_in_any_story(self):
        root = 'tests/testing_data/validator/orphan_intents'
        domain_path = 'tests/testing_data/validator/orphan_intents/domain.yml'
        nlu_path = 'tests/testing_data/validator/orphan_intents/data'
        config_path = 'tests/testing_data/validator/orphan_intents/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert validator.summary['intents'][0] == 'The intent \'affirm\' is not used in any story.'
        assert validator.summary['intents'][1] == 'The intent \'bot_challenge\' is not used in any story.'
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_repeated_training_example(self):
        root = 'tests/testing_data/validator/common_training_examples'
        domain_path = 'tests/testing_data/validator/common_training_examples/domain.yml'
        nlu_path = 'tests/testing_data/validator/common_training_examples/data'
        config_path = 'tests/testing_data/validator/common_training_examples/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert not validator.summary.get('intents')
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert validator.summary['training_examples'][
                   0] == 'The example \'no\' was found labeled with multiple different intents in the training data. Each annotated message should only appear with one intent. You should fix that conflict The example is labeled with: deny, refute.'
        assert validator.summary['training_examples'][
                   1] == 'The example \'never\' was found labeled with multiple different intents in the training data. Each annotated message should only appear with one intent. You should fix that conflict The example is labeled with: deny, refute.'
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_utterance_in_story_not_in_domain(self):
        root = 'tests/testing_data/validator/utterance_missing_in_domain'
        domain_path = 'tests/testing_data/validator/utterance_missing_in_domain/domain.yml'
        nlu_path = 'tests/testing_data/validator/utterance_missing_in_domain/data'
        config_path = 'tests/testing_data/validator/utterance_missing_in_domain/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert not validator.summary.get('intents')
        assert validator.summary['stories'][
                   0] == 'The action \'utter_goodbye\' is used in the stories, but is not a valid utterance action. Please make sure the action is listed in your domain and there is a template defined with its name.'
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_utterance_not_used_in_any_story(self):
        root = 'tests/testing_data/validator/orphan_utterances'
        domain_path = 'tests/testing_data/validator/orphan_utterances/domain.yml'
        nlu_path = 'tests/testing_data/validator/orphan_utterances/data'
        config_path = 'tests/testing_data/validator/orphan_utterances/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert not validator.summary.get('intents')
        assert 'The utterance \'utter_good_feedback\' is not used in any story.' in validator.summary['utterances']
        assert 'The utterance \'utter_bad_feedback\' is not used in any story.' in validator.summary['utterances']
        assert set(validator.summary['utterances']) == {"The utterance 'utter_bad_feedback' is not used in any story.",
                                                        "The utterance 'utter_iamabot' is not used in any story.",
                                                        "The utterance 'utter_feedback' is not used in any story.",
                                                        "The utterance 'utter_good_feedback' is not used in any story."}
        assert not validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_valid_training_data(self):
        root = 'tests/testing_data/validator/valid'
        domain_path = 'tests/testing_data/validator/valid/domain.yml'
        nlu_path = 'tests/testing_data/validator/valid/data'
        config_path = 'tests/testing_data/validator/valid/config.yml'
        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data()
        assert not validator.summary.get('intents')
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_valid_training_data_with_multiflow_stories(self):
        root = 'tests/testing_data/validator/valid_with_multiflow'
        domain_path = 'tests/testing_data/validator/valid_with_multiflow/domain.yml'
        nlu_path = 'tests/testing_data/validator/valid_with_multiflow/data'
        config_path = 'tests/testing_data/validator/valid_with_multiflow/config.yml'
        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data()
        assert not validator.summary.get('intents')
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert not validator.summary.get('multiflow_stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary.get('config')

    @pytest.mark.asyncio
    async def test_validate_invalid_training_file_path(self):
        root = 'tests/testing_data/invalid_path/domain.yml'
        domain_path = 'tests/testing_data/invalid_path/domain.yml'
        nlu_path = 'tests/testing_data/validator/intent_name_mismatch/data'
        config_path = 'tests/testing_data/validator/intent_name_mismatch/config.yml'
        with pytest.raises(AppException):
            await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)

    @pytest.mark.asyncio
    async def test_validate_config_with_invalid_pipeline(self):
        root = 'tests/testing_data/validator/invalid_config'
        domain_path = 'tests/testing_data/validator/invalid_config/domain.yml'
        nlu_path = 'tests/testing_data/validator/invalid_config/data'
        config_path = 'tests/testing_data/validator/invalid_config/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert not validator.summary.get('intents')
        assert not validator.summary.get('utterances')
        assert not validator.summary.get('stories')
        assert not validator.summary.get('training_examples')
        assert not validator.summary.get('domain')
        assert not validator.summary['config'] == "Failed to load the component 'CountTokenizer'"

    @pytest.mark.asyncio
    async def test_validate_invalid_multiflow_stories(self):
        root = 'tests/testing_data/invalid_yml_multiflow'
        domain_path = 'tests/testing_data/invalid_yml_multiflow/domain.yml'
        nlu_path = 'tests/testing_data/invalid_yml_multiflow/data'
        config_path = 'tests/testing_data/invalid_yml_multiflow/config.yml'
        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        with pytest.raises(AppException, match="Invalid multiflow_stories.yml. Check logs!"):
            validator.validate_training_data()

    @pytest.mark.asyncio
    async def test_validate_utterance_not_used_in_any_multiflow_story(self):
        root = 'tests/testing_data/validator/unused_utterances_multiflow'
        domain_path = 'tests/testing_data/validator/unused_utterances_multiflow/domain.yml'
        nlu_path = 'tests/testing_data/validator/unused_utterances_multiflow/data'
        config_path = 'tests/testing_data/validator/unused_utterances_multiflow/config.yml'
        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        with pytest.raises(AppException):
            validator.validate_training_data()

        validator.validate_training_data(False)
        assert validator.summary['utterances'][0] == "The utterance 'utter_more_info' is not used in any story."

    @pytest.mark.asyncio
    async def test_validate_intent_in_multiflow_story_not_in_domain(self):
        root = 'tests/testing_data/validator/unused_intents_multiflow'
        domain_path = 'tests/testing_data/validator/unused_intents_multiflow/domain.yml'
        nlu_path = 'tests/testing_data/validator/unused_intents_multiflow/data'
        config_path = 'tests/testing_data/validator/unused_intents_multiflow/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert validator.summary['intents'][0] == "The intent 'more_info' is used in your multiflow_stories, but it is not listed in the domain file. You should add it to your domain file!"

    @pytest.mark.asyncio
    async def test_validate_intent_not_used_in_any_multiflow_story(self):
        root = 'tests/testing_data/validator/orphan_domain_intents_multiflow'
        domain_path = 'tests/testing_data/validator/orphan_domain_intents_multiflow/domain.yml'
        nlu_path = 'tests/testing_data/validator/orphan_domain_intents_multiflow/data'
        config_path = 'tests/testing_data/validator/orphan_domain_intents_multiflow/config.yml'
        with pytest.raises(AppException):
            validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
            validator.validate_training_data()

        validator = await TrainingDataValidator.from_training_files(nlu_path, domain_path, config_path, root)
        validator.validate_training_data(False)
        assert validator.summary['intents'][0] == "The intent 'more_info' is not used in any story."

    def test_validate_http_action_empty_content(self):
        test_dict = {'http_action': []}
        assert TrainingDataValidator.validate_custom_actions(test_dict)
        assert TrainingDataValidator.validate_custom_actions([{}])

    def test_validate_http_action_error_duplicate(self):
        test_dict = {'http_action': [{'action_name': "act2", 'http_url': "http://www.alphabet.com", "response": 'asdf',
                                      "request_method": 'POST'},
                                     {'action_name': "act2", 'http_url': "http://www.alphabet.com", "response": 'asdf',
                                      "request_method": 'POST'}]}
        errors = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Duplicate http action found: act2' in errors[1]['http_actions']

    def test_validate_http_action_error_missing_field(self):
        test_dict = {
            'http_action': [{'http_url': "http://www.alphabet.com", "response": 'asdf', "request_method": 'POST'}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert "Required http action fields" in errors['http_actions'][0]

    def test_validate_http_action_invalid_request_method(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'slot', "value": 'slot'}],
                                      "request_method": "OPTIONS", "response": "${RESPONSE}"}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Invalid request method: rain_today' in errors['http_actions']

    def test_validate_http_action_empty_params_list(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": '', "parameter_type": '', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Invalid params_list for http action: rain_today' in errors['http_actions']

    def test_validate_http_action_empty_headers(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "headers": [],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)

    def test_validate_http_action_header_with_empty_key(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "headers": [{"key": '', "parameter_type": '', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Invalid headers for http action: rain_today' in errors['http_actions']

    def test_validate_http_action_header_with_no_parameter_type(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "headers": [{"key": 'location', "parameter_type": '', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Invalid headers for http action: rain_today' in errors['http_actions']

    def test_validate_http_action_header_with_empty_slot_value(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "headers": [
                                          {"key": 'location', "parameter_type": 'value', "value": 'Mumbai'},
                                          {"key": 'username', "parameter_type": 'slot', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        TrainingDataValidator.validate_custom_actions(test_dict)
        assert test_dict['http_action'][0]['headers'][1]['value'] == 'username'

    def test_validate_http_action_header(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "headers": [
                                          {"key": 'location', "parameter_type": 'value', "value": 'Mumbai'},
                                          {"key": 'paid_user', "parameter_type": 'slot', "value": ''},
                                          {"key": 'username', "parameter_type": 'sender_id'},
                                          {"key": 'user_msg', "parameter_type": 'user_message'}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        TrainingDataValidator.validate_custom_actions(test_dict)
        assert test_dict['http_action'][0]['headers'][1]['value'] == 'paid_user'

    def test_validate_http_action_header_invalid_parameter_type(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "headers": [
                                          {"key": 'location', "parameter_type": 'text', "value": 'Mumbai'}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Invalid headers for http action: rain_today' in errors['http_actions']

    def test_validate_http_action_empty_params_list_2(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": '', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        is_data_invalid, errors, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert 'Invalid params_list for http action: rain_today' in errors['http_actions']

    def test_validate_http_action_empty_slot_type(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [
                                          {"key": 'location', "parameter_type": 'value', "value": 'Mumbai'},
                                          {"key": 'username', "parameter_type": 'slot', "value": ''},
                                          {"key": 'username', "parameter_type": 'user_message', "value": ''},
                                          {"key": 'username', "parameter_type": 'sender_id', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)
        assert test_dict['http_action'][0]['params_list'][1]['value'] == 'username'

    def test_validate_http_action_params_list_4(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'value', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)

        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'value', "value": None}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)

    def test_validate_http_action_empty_params_list_5(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)

    def test_validate_http_action_empty_params_list_6(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [], "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)

    def test_validate_http_action_empty_params_list_7(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'sender_id', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        assert TrainingDataValidator.validate_custom_actions(test_dict)

    def test_validate_custom_actions(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'sender_id', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"}]}
        is_data_invalid, error_summary, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert not is_data_invalid
        assert error_summary == {'http_actions': [], 'email_actions': [], 'form_validation_actions': [],
                                 'google_search_actions': [], 'jira_actions': [], 'slot_set_actions': [],
                                 'zendesk_actions': [], 'pipedrive_leads_actions': [], 'prompt_actions': []}
        assert component_count

    def test_validate_custom_actions_with_errors(self):
        test_dict = {"http_action": [{"action_name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'sender_id', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"},
                                     {"action_name": "rain_today1", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'local', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"},
                                     {"action_name": "rain_today2", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'slot', "value": ''}],
                                      "request_method": "OPTIONS", "response": "${RESPONSE}"},
                                     {"action_name": "rain_today3", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'intent', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"},
                                     {"action_name": "rain_today4", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'chat_log', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"},
                                     {"name": "rain_today", "http_url": "http://f2724.kairon.io/",
                                      "params_list": [{"key": 'location', "parameter_type": 'chat_log', "value": ''}],
                                      "request_method": "GET", "response": "${RESPONSE}"},
                                     [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]
                                     ],
                     'slot_set_action': [
                         {'name': 'set_cuisine', 'set_slots': [{'name': 'cuisine', 'type': 'from_value', 'value': '100'}]},
                         {'name': 'set_num_people', 'set_slots': [{'name': 'num_people', 'type': 'reset_slot'}]},
                         {'': 'action', 'set_slots': [{'name': 'outside_seat', 'type': 'slot', 'value': 'yes'}]},
                         {'name': 'action', 'set_slots': [{'name': 'outside_seat', 'type': 'slot'}]},
                         {'name': 'set_num_people', 'set_slots': [{'name': 'num_people', 'type': 'reset_slot', 'value': {'resp': 1}}]},
                         {'name': 'set_multiple', 'set_slots': [{'name': 'num_p', 'type': 'reset_slot'}, {'name': 'num_people', 'type': 'from_value', 'value': {'resp': 1}}]},
                         {'name': 'set_none', 'set_slots': None},
                         {'name': 'set_no_name', 'set_slots': [{' ': 'num_people', 'type': 'reset_slot', 'value': {'resp': 1}}]},
                         {'name': 'set_none_name', 'set_slots': [{None: 'num_people', 'type': 'reset_slot', 'value': {'resp': 1}}]},
                         [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]],
                     'form_validation_action': [
                         {'name': 'validate_action', 'slot': 'cuisine', 'validation_semantic': None,
                          'valid_response': 'valid slot value', 'invalid_response': 'invalid slot value',
                          'slot_set': {'type': 'current', 'value': ''}},
                         {'name': 'validate_action', 'slot': 'num_people', 
                          'validation_semantic': 'if(size(slot[''num_people''])<10) { return true; } else { return false; }',
                          'valid_response': 'valid value', 'invalid_response': 'invalid value',
                          'slot_set': {'type': '', 'value': ''}
                          },
                         {'slot': 'outside_seat'},
                         {'name': 'validate_action', 'slot': 'num_people', 'slot_set': {'type': 'slot', 'value': ''}},
                         {'name': 'validate_action_one', 'slot': 'num_people'},
                         {'name': 'validate_action', 'slot': 'num_people', 'slot_set': {'type': 'current', 'value': 'Khare'}},
                         {'': 'validate_action', 'slot': 'preference', 'slot_set': {'type': 'form', 'value': ''}},
                         {'name': 'validate_action_again', 'slot': 'num_people', 'slot_set': {'type': 'custom', 'value': ''}},
                         [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]],
                     'email_action': [{'action_name': 'send_mail', 'smtp_url': 'smtp.gmail.com', 'smtp_port': '587',
                                       'smtp_password': '234567890', 'from_email': 'test@digite.com',
                                       'subject': 'bot falled back', 'to_email': 'test@digite.com',
                                       'response': 'mail sent'},
                                      {'action_name': 'send_mail1', 'smtp_url': 'smtp.gmail.com', 'smtp_port': '587',
                                       'smtp_userid': 'asdfghjkl',
                                       'smtp_password': 'asdfghjkl',
                                       'from_email': 'test@digite.com', 'subject': 'bot fallback',
                                       'to_email': 'test@digite.com', 'response': 'mail sent',
                                       'tls': False},
                                      {'action_name': 'send_mail', 'smtp_url': 'smtp.gmail.com', 'smtp_port': '587',
                                       'smtp_password': '234567890', 'from_email': 'test@digite.com',
                                       'subject': 'bot falled back', 'to_email': 'test@digite.com',
                                       'response': 'mail sent'},
                                      {'name': 'send_mail', 'smtp_url': 'smtp.gmail.com', 'smtp_port': '587',
                                       'smtp_password': '234567890', 'from_email': 'test@digite.com',
                                       'subject': 'bot falled back', 'to_email': 'test@digite.com',
                                       'response': 'mail sent'},
                                      [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]
                                      ],
                     'jira_action': [{'name': 'jira', 'url': 'http://domain.atlassian.net',
                                      'user_name': 'test@digite.com', 'api_token': '123456', 'project_key': 'KAI',
                                      'issue_type': 'Subtask', 'parent_key': 'HEL', 'summary': 'demo request',
                                      'response': 'issue created'},
                                     {'name': 'jira1', 'url': 'http://domain.atlassian.net',
                                      'user_name': 'test@digite.com', 'api_token': '234567',
                                      'project_key': 'KAI', 'issue_type': 'Bug', 'summary': 'demo request',
                                      'response': 'issue created'},
                                     {'name': 'jira2', 'url': 'http://domain.atlassian.net',
                                      'user_name': 'test@digite.com', 'api_token': '234567',
                                      'project_key': 'KAI', 'issue_type': 'Subtask', 'summary': 'demo request',
                                      'response': 'ticket created'},
                                     {'name': 'jira', 'url': 'http://domain.atlassian.net',
                                      'user_name': 'test@digite.com', 'api_token': '24567',
                                      'project_key': 'KAI', 'issue_type': 'Task', 'summary': 'demo request',
                                      'response': 'ticket created'},
                                     {'action_name': 'jira', 'url': 'http://domain.atlassian.net',
                                      'user_name': 'test@digite.com', 'api_token': '24567',
                                      'project_key': 'KAI', 'issue_type': 'Task', 'summary': 'demo request',
                                      'response': 'ticket created'},
                                     [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]],
                     'zendesk_action': [{'name': 'zendesk', 'subdomain': 'digite', 'user_name': 'test@digite.com',
                                         'api_token': '123456', 'subject': 'demo request',
                                         'response': 'ticket created'},
                                        {'action_name': 'zendesk1', 'subdomain': 'digite',
                                         'user_name': 'test@digite.com', 'api_token': '123456',
                                         'subject': 'demo request', 'response': 'ticket created'},
                                        {'name': 'zendesk2', 'subdomain': 'digite', 'user_name': 'test@digite.com',
                                         'api_token': '123456', 'subject': 'demo request',
                                         'response': 'ticket created'},
                                        [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]],
                     'google_search_action': [
                         {'name': 'google_search', 'api_key': '1231234567', 'search_engine_id': '2345678'},
                         {'name': 'google_search1', 'api_key': '1231234567', 'search_engine_id': '2345678',
                          'failure_response': 'failed', 'num_results': 10},
                         {'name': 'google_search2', 'api_key': '1231234567', 'search_engine_id': '2345678',
                          'failure_response': 'failed to search', 'num_results': '1'},
                         {'name': 'google_search', 'api_key': '1231234567', 'search_engine_id': '2345678',
                          'failure_response': 'failed to search', 'num_results': ''},
                         [{'action_name': '', 'smtp_url': '', 'smtp_port': '', 'smtp_userid': ''}]],
                     'pipedrive_leads_action': [
                         {'name': 'action_pipedrive_leads', 'domain': 'https://digite751.pipedrive.com',
                          'api_token': '2345678dfghj', 'metadata': {
                             'name': 'name', 'org_name': 'organization', 'email': 'email', 'phone': 'phone'
                         }, 'title': 'new lead detected', 'response': 'lead_created'},
                         {'name': 'action_create_lead', 'domain': 'https://digite75.pipedrive.com',
                          'api_token': '2345678dfghj', 'metadata': {
                             'name': 'name'}, 'title': 'new lead detected', 'response': 'lead_created'},
                         {'name': 'pipedrive_leads_action', 'domain': 'https://digite751.pipedrive.com',
                          'api_token': '2345678dfghj', 'metadata': {
                             'org_name': 'organization', 'email': 'email', 'phone': 'phone'
                         }, 'title': 'new lead detected', 'response': 'lead_created'},
                         {'domain': 'https://digite751.pipedrive.com', 'api_token': '2345678dfghj', 'metadata': {
                             'name': 'name', 'org_name': 'organization', 'email': 'email', 'phone': 'phone'
                         }, 'title': 'new lead detected', 'response': 'lead_created'},
                         {'name': 'action_pipedrive_leads', 'domain': 'https://digite751.pipedrive.com',
                          'api_token': '2345678dfghj', 'metadata': {
                             'name': 'name', 'org_name': 'organization', 'email': 'email', 'phone': 'phone'
                         }, 'title': 'new lead detected', 'response': 'lead_created'}
                     ],
                     'prompt_action': [
                         {'name': 'prompt_action_invalid_query_prompt',
                          'llm_prompts': [
                              {'name': 'Similarity Prompt',
                               'instructions': 'Answer question based on the context above, if answer is not in the context go check previous logs.',
                               'type': 'user', 'source': 'bot_content', 'is_enabled': True},
                              {'name': '',
                               'data': 'A programming language is a system of notation for writing computer programs.[1] Most programming languages are text-based formal languages, but they may also be graphical. They are a kind of computer language.',
                               'instructions': 'Answer according to the context', 'type': 'query',
                               'source': 'history', 'is_enabled': True}],
                          "failure_message": DEFAULT_NLU_FALLBACK_RESPONSE, "top_results": 40,
                          "similarity_threshold": 2,
                          "num_bot_responses": 5},
                         {'name': 'prompt_action_invalid_num_bot_responses',
                          'llm_prompts': [
                              {'name': 'System Prompt', 'data': 'You are a personal assistant.', 'type': 'system',
                               'source': 'static', 'is_enabled': True},
                              {'name': 'Similarity Prompt',
                               'instructions': 'Answer question based on the context above, if answer is not in the context go check previous logs.',
                               'type': 'user', 'source': 'bot_content', 'is_enabled': True},
                              {'name': 'Query Prompt',
                               'data': 100,
                               'instructions': '', 'type': 'query',
                               'source': 'static', 'is_enabled': True},
                              {'name': 'Query Prompt three',
                               'data': '',
                               'instructions': '', 'type': 'query',
                               'source': 'static', 'is_enabled': True}
                          ],
                          "failure_message": DEFAULT_NLU_FALLBACK_RESPONSE, "top_results": 10,
                          "similarity_threshold": 0.70,
                          "num_bot_responses": 15},
                         {'name': 'prompt_action_with_invalid_system_prompt_source',
                          'llm_prompts': [
                              {'name': 'System Prompt', 'data': 'You are a personal assistant.', 'type': 'system',
                               'source': 'history',
                               'is_enabled': True},
                              {'name': 'Similarity Prompt',
                               'instructions': 'Answer question based on the context above, if answer is not in the context go check previous logs.',
                               'type': 'user', 'source': 'bot_content', 'is_enabled': True},
                              {'name': 'Similarity Prompt two',
                               'instructions': 'Answer question based on the context above, if answer is not in the context go check previous logs.',
                               'type': 'user', 'source': 'bot_content', 'is_enabled': True}
                          ],
                          "failure_message": DEFAULT_NLU_FALLBACK_RESPONSE, "top_results": 10,
                          "similarity_threshold": 0.70, "num_bot_responses": 5,
                          'hyperparameters': {'temperature': 3.0, 'max_tokens': 5000, 'model': 'gpt - 3.5 - turbo',
                                       'top_p': 4,
                                       'n': 10, 'stream': False, 'stop': {}, 'presence_penalty': 5,
                                       'frequency_penalty': 5, 'logit_bias': []}},
                         {'name': 'prompt_action_with_no_llm_prompts',
                          "failure_message": DEFAULT_NLU_FALLBACK_RESPONSE, "top_results": 10,
                          "similarity_threshold": 0.70, "num_bot_responses": 5,
                          'hyperparameters': {'temperature': 3.0, 'max_tokens': 300, 'model': 'gpt - 3.5 - turbo',
                                              'top_p': 0.0,
                                              'n': 1, 'stream': False, 'stop': None, 'presence_penalty': 0.0,
                                              'frequency_penalty': 0.0, 'logit_bias': {}}},
                         {'name': 'test_add_prompt_action_one',
                          'llm_prompts': [
                              {'name': 'System Prompt', 'data': 'You are a personal assistant.', 'type': 'system',
                               'source': 'static', 'is_enabled': True},
                              {'name': 'History Prompt', 'type': 'user', 'source': 'history', 'is_enabled': True}],
                          "dispatch_response": False
                          },
                         {'name': 'test_add_prompt_action_one',
                          'llm_prompts': [
                              {'name': 'System Prompt', 'data': 'You are a personal assistant.', 'type': 'system',
                               'source': 'static', 'is_enabled': True},
                              {'name': 'History Prompt', 'type': 'user', 'source': 'history', 'is_enabled': True}],
                          "dispatch_response": False
                          },
                         [{'name': 'test_add_prompt_action_faq_action_in_list',
                           'llm_prompts': [
                               {'name': 'System Prompt', 'data': 'You are a personal assistant.', 'type': 'system',
                                'source': 'static', 'is_enabled': True},
                               {'name': 'History Prompt', 'type': 'user', 'source': 'history', 'is_enabled': True}],
                           "dispatch_response": False
                           }],
                         {'name': 'test_add_prompt_action_three',
                          'llm_prompts': [
                              {'name': 'System Prompt', 'data': 'You are a personal assistant.', 'type': 'system',
                               'source': 'static', 'is_enabled': True},
                              {'name': 'System Prompt two', 'data': 'You are a personal assistant.', 'type': 'system',
                               'source': 'static', 'is_enabled': True},
                              {'name': 'Test Prompt', 'type': 'test', 'source': 'test', 'is_enabled': True},
                              {'name': 'Similarity Prompt', 'instructions': 50, 'type': 1, 'source': 2, 'is_enabled': True},
                              {'name': 'Http action Prompt', 'data': '', 'instructions': 'Answer according to the context',
                               'type': 'user', 'source': 'action', 'is_enabled': True},
                              {'name': 'Identification Prompt', 'data': '', 'instructions': 'Answer according to the context',
                               'type': 'user', 'source': 'slot', 'is_enabled': True},
                              {'name': 'History Prompt one', 'type': 'user', 'source': 'history', 'is_enabled': True},
                              {'name': 'History Prompt two', 'type': 'user', 'source': 'history', 'is_enabled': True}
                          ],
                          "dispatch_response": False,
                          'hyperparameters': {'temperature': 3.0, 'max_tokens': 5000, 'model': 'gpt - 3.5 - turbo',
                                              'top_p': 4,
                                              'n': 10, 'stream': False, 'stop': ['a', 'b', 'c', 'd', 'e'], 'presence_penalty': 5,
                                              'frequency_penalty': 5, 'logit_bias': []}
                          },
                     ]}
        is_data_invalid, error_summary, component_count = TrainingDataValidator.validate_custom_actions(test_dict)
        assert is_data_invalid
        assert len(error_summary['http_actions']) == 4
        assert len(error_summary['slot_set_actions']) == 7
        assert len(error_summary['form_validation_actions']) == 10
        assert len(error_summary['email_actions']) == 3
        assert len(error_summary['jira_actions']) == 4
        assert len(error_summary['google_search_actions']) == 2
        assert len(error_summary['zendesk_actions']) == 2
        assert len(error_summary['pipedrive_leads_actions']) == 3
        assert len(error_summary['prompt_actions']) == 46
        required_fields_error = error_summary["prompt_actions"][18]
        assert re.match(r"Required fields .* not found in action: prompt_action_with_no_llm_prompts", required_fields_error)
        del error_summary["prompt_actions"][18]
        assert error_summary['prompt_actions'] == [
            'top_results should not be greater than 30 and of type int: prompt_action_invalid_query_prompt',
            'similarity_threshold should be within 0.3 and 1 and of type int or float: prompt_action_invalid_query_prompt',
            'System prompt is required', 'Query prompt must have static source',
            'Name cannot be empty', 'System prompt is required',
            'num_bot_responses should not be greater than 5 and of type int: prompt_action_invalid_num_bot_responses',
            'data field in prompts should of type string.', 'data is required for static prompts',
            'Temperature must be between 0.0 and 2.0!', 'max_tokens must be between 5 and 4096!',
            'top_p must be between 0.0 and 1.0!', 'n must be between 1 and 5!',
            'presence_penality must be between -2.0 and 2.0!', 'frequency_penalty must be between -2.0 and 2.0!',
            'logit_bias must be a dictionary!', 'System prompt must have static source',
            'Only one bot_content source can be present',
            'Duplicate action found: test_add_prompt_action_one',
            'Invalid action configuration format. Dictionary expected.',
            'Temperature must be between 0.0 and 2.0!', 'max_tokens must be between 5 and 4096!',
            'top_p must be between 0.0 and 1.0!', 'n must be between 1 and 5!',
            'Stop must be None, a string, an integer, or an array of 4 or fewer strings or integers.',
            'presence_penality must be between -2.0 and 2.0!',
            'frequency_penalty must be between -2.0 and 2.0!',
            'logit_bias must be a dictionary!', 'Only one system prompt can be present',
            'Invalid prompt type', 'Invalid prompt source', 'Only one system prompt can be present',
            'Invalid prompt type', 'Invalid prompt source', 'type in LLM Prompts should be of type string.',
            'source in LLM Prompts should be of type string.', 'Instructions in LLM Prompts should be of type string.',
            'Only one system prompt can be present', 'Data must contain action name',
            'Only one system prompt can be present', 'Data must contain slot name',
            'Only one system prompt can be present', 'Only one system prompt can be present',
            'Only one system prompt can be present', 'Only one history source can be present']
        assert component_count == {'http_actions': 7, 'slot_set_actions': 10, 'form_validation_actions': 9,
                                   'email_actions': 5, 'google_search_actions': 5, 'jira_actions': 6,
                                   'zendesk_actions': 4, 'pipedrive_leads_actions': 5, 'prompt_actions': 8}

    def test_validate_multiflow_stories(self):
        steps_mf_one = [
            {"step": {"name": "greet", "type": "INTENT", "node_id": "1", "component_id": "ksos09"},
             "connections": [{"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ksos09"}]
             },
            {"step": {"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ksos09"},
             "connections": None
             },
            {"step": {"name": "mood", "type": "INTENT", "node_id": "3", "component_id": "ksos09"},
             "connections": [{"name": "utter_mood", "type": "BOT", "node_id": "4", "component_id": "ksos09"}]
             },
            {"step": {"name": "utter_mood", "type": "BOT", "node_id": "4", "component_id": "ksos09"},
             "connections": None
             },
        ]
        steps_mf_two = [
            {"step": {"name": "greet", "type": "INTENT", "node_id": "1", "component_id": "ksos09"},
             "connections": [{"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ksos09"}]
             },
            {"step": {"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ksos09"},
             "connections": None
             },
            {"step": {"name": "mood", "type": "INTENT", "node_id": "3", "component_id": "ksos09"},
             "connections": [{"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ksos09"}]
             }
        ]
        steps_mf_three = [
            {"step": {"name": "greet", "type": "BOT", "node_id": "1", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_time", "type": "BOT", "node_id": "2", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "utter_time", "type": "BOT", "node_id": "2", "component_id": "NKUPKJ"},
             "connections": [{"name": "more_queries", "type": "INTENT", "node_id": "3", "component_id": "NKUPKJ"},
                             {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_goodbye", "type": "BOT", "node_id": "5", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "utter_goodbye", "type": "BOT", "node_id": "5", "component_id": "NKUPKJ"},
             "connections": None
             },
            {"step": {"name": "utter_more_queries", "type": "BOT", "node_id": "6", "component_id": "NKUPKJ"},
             "connections": None
             },
            {"step": {"name": "more_queries", "type": "INTENT", "node_id": "3", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_more_queries", "type": "BOT", "node_id": "6", "component_id": "NKUPKJ"}]
             }
        ]
        steps_mf_four = [
            {"step": {"name": "greet", "type": "INTENT", "node_id": "1", "component_id": "ppooakak"},
             "connections": [{"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ppooakak"}]
             },
            {"step": {"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "ppooakak"},
             "connections": [{"name": "utter_qoute", "type": "BOT", "node_id": "3", "component_id": "ppooakak"},
                             {"name": "utter_thought", "type": "BOT", "node_id": "4", "component_id": "ppooakak"}]
             },
            {"step": {"name": "utter_thought", "type": "BOT", "node_id": "4", "component_id": "ppooakak"},
             "connections": [{"name": "more_queries", "type": "INTENT", "node_id": "5", "component_id": "ppooakak"}]
             },
            {"step": {"name": "more_queries", "type": "INTENT", "node_id": "5", "component_id": "ppooakak"},
             "connections": [{"name": "goodbye", "type": "INTENT", "node_id": "6", "component_id": "ppooakak"}]
             },
            {"step": {"name": "utter_qoute", "type": "BOT", "node_id": "3", "component_id": "ppooakak"},
             "connections": [{"name": "goodbye", "type": "INTENT", "node_id": "6", "component_id": "ppooakak"}]
             },
            {"step": {"name": "goodbye", "type": "INTENT", "node_id": "6", "component_id": "ppooakak"},
             "connections": [{"name": "utter_qoute", "type": "BOT", "node_id": "3", "component_id": "ppooakak"}]
             },
            {"step": {"name": "goodbye", "type": "INTENT", "node_id": "6", "component_id": "ppooakak"},
             "connections": None
             }
        ]
        steps_mf_five = [
            {"step": {"name": "greet", "type": "INTENT", "node_id": "1", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_time", "type": "INTENT", "node_id": "2", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "utter_time", "type": "INTENT", "node_id": "2", "component_id": "NKUPKJ"},
             "connections": [{"name": "more_queries", "type": "INTENT", "node_id": "3", "component_id": "NKUPKJ"},
                             {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_goodbye", "type": "BOT", "node_id": "5", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "utter_goodbye", "type": "BOT", "node_id": "5", "component_id": "NKUPKJ"},
             "connections": None
             },
            {"step": {"name": "utter_more_queries", "type": "BOT", "node_id": "6", "component_id": "NKUPKJ"},
             "connections": None
             },
            {"step": {"name": "more_queries", "type": "INTENT", "node_id": "3", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_more_queries", "type": "BOT", "node_id": "4", "component_id": "NKUPKJ"}]
             }
        ]
        steps_mf_six = [
            {"step": {"name": "heyyy", "type": "INTENT", "node_id": "1", "component_id": "ppooakak"},
             "connections": [{"name": "utter_heyyy", "type": "BOT", "node_id": "2", "component_id": "ppooakak"},
                             {"name": "utter_greet", "type": "BOT", "node_id": "3", "component_id": "ppooakak"}]
             },
            {"step": {"name": "utter_greet", "type": "BOT", "node_id": "3", "component_id": "ppooakak"},
             "connections": [{"name": "more_queriesss", "type": "INTENT", "node_id": "4", "component_id": "ppooakak"},
                             {"name": "goodbyeee", "type": "INTENT", "node_id": "5", "component_id": "ppooakak"}]
             },
            {"step": {"name": "goodbyeee", "type": "INTENT", "node_id": "5", "component_id": "ppooakak"},
             "connections": [{"name": "utter_goodbyeee", "type": "BOT", "node_id": "6", "component_id": "ppooakak"}]
             },
            {"step": {"name": "utter_goodbyeee", "type": "BOT", "node_id": "6", "component_id": "ppooakak"},
             "connections": None
             },
            {"step": {"name": "utter_more_queriesss", "type": "BOT", "node_id": "7", "component_id": "ppooakak"},
             "connections": None
             },
            {"step": {"name": "more_queriesss", "type": "INTENT", "node_id": "4", "component_id": "ppooakak"},
             "connections": [
                 {"name": "utter_more_queriesss", "type": "BOT", "node_id": "7", "component_id": "ppooakak"}]
             },
            {"step": {"name": "utter_heyyy", "type": "BOT", "node_id": "2", "component_id": "ppooakak"},
             "connections": None
             }
        ]
        steps_mf_seven = [
            {"step": {"name": "greeting", "type": "INTENT", "node_id": "1", "component_id": "637d0j9GD059jEwt2jPnlZ7I"},
             "connections": [
                 {"name": "utter_greeting", "type": "BOT", "node_id": "2", "component_id": "63uNJw1QvpQZvIpP07dxnmFU"}]
             },
            {"step": {"name": "utter_greeting", "type": "BOT", "node_id": "2",
                      "component_id": "63uNJw1QvpQZvIpP07dxnmFU"},
             "connections": [
                 {"name": "mood", "type": "INTENT", "node_id": "3", "component_id": "633w6kSXuz3qqnPU571jZyCv"},
                 {"name": "games", "type": "SLOT", "value": {"1": "cricket"}, "node_id": "4",
                  "component_id": "63WKbWs5K0ilkujWJQpXEXGD"}]
             },
            {"step": {"name": "games", "type": "SLOT", "value": {"1": "cricket"}, "node_id": "4",
                      "component_id": "63WKbWs5K0ilkujWJQpXEXGD"},
             "connections": [
                 {"name": "utter_games", "type": "BOT", "node_id": "5", "component_id": "63gm5BzYuhC1bc6yzysEnN4E"}]
             },
            {"step": {"name": "utter_games", "type": "BOT", "node_id": "5",
                      "component_id": "63gm5BzYuhC1bc6yzysEnN4E"},
             "connections": None
             },
            {"step": {"name": "utter_mood", "type": "BOT", "node_id": "6",
                      "component_id": "634a9bwPPj2y3zF5HOVgLiXx"},
             "connections": None
             },
            {"step": {"name": "mood", "type": "INTENT", "node_id": "3",
                      "component_id": "633w6kSXuz3qqnPU571jZyCv"},
             "connections": [{"name": "utter_mood", "type": "BOT", "node_id": "6",
                              "component_id": "634a9bwPPj2y3zF5HOVgLiXx"}]
             }
        ]
        steps_mf_eight = [
            {"step": {"name": "hello", "type": "INTENT", "node_id": "1", "component_id": "637d0j9GD059jEwt2jPnlZ7I"},
             "connections": [
                 {"name": "utter_hello", "type": "BOT", "node_id": "2", "component_id": "63uNJw1QvpQZvIpP07dxnmFU"}]
             },
            {"step": {"name": "utter_hello", "type": "BOT", "node_id": "2", "component_id": "63uNJw1QvpQZvIpP07dxnmFU"},
             "connections": [
                 {"name": "mood", "type": "INTENT", "value": "Good", "node_id": "3",
                  "component_id": "633w6kSXuz3qqnPU571jZyCv"},
                 {"name": "games", "type": "INTENT", "node_id": "4", "component_id": "63WKbWs5K0ilkujWJQpXEXGD"}]
             },
            {"step": {"name": "games", "type": "INTENT", "node_id": "4", "component_id": "63WKbWs5K0ilkujWJQpXEXGD"},
             "connections": [
                 {"name": "utter_games", "type": "BOT", "node_id": "5", "component_id": "63gm5BzYuhC1bc6yzysEnN4E"}]
             },
            {"step": {"name": "utter_games", "type": "BOT", "node_id": "5",
                      "component_id": "63gm5BzYuhC1bc6yzysEnN4E"},
             "connections": None
             },
            {"step": {"name": "utter_mood", "type": "BOT", "node_id": "6",
                      "component_id": "634a9bwPPj2y3zF5HOVgLiXx"},
             "connections": None
             },
            {"step": {"name": "mood", "type": "INTENT", "value": "Good", "node_id": "3",
                      "component_id": "633w6kSXuz3qqnPU571jZyCv"},
             "connections": [{"name": "utter_mood", "type": "BOT", "node_id": "6",
                              "component_id": "634a9bwPPj2y3zF5HOVgLiXx"}]
             }
        ]
        steps_mf_nine = [
            {"step": {"name": "weathery", "type": "INTENT", "node_id": "1", "component_id": "637d0j9GD059jEwt2jPnlZ7I"},
             "connections": [
                 {"name": "utter_weathery", "type": "BOT", "node_id": "2", "component_id": "63uNJw1QvpQZvIpP07dxnmFU"}]
             },
            {"step": {"name": "utter_weathery", "type": "BOT", "node_id": "2",
                      "component_id": "63uNJw1QvpQZvIpP07dxnmFU"},
             "connections": [
                 {"name": "sunny", "type": "INTENT", "node_id": "3", "component_id": "633w6kSXuz3qqnPU571jZyCv"},
                 {"name": "rainy", "type": "INTENT", "node_id": "4",
                  "component_id": "63WKbWs5K0ilkujWJQpXEXGD"}]
             },
            {"step": {"name": "sunny", "type": "INTENT", "node_id": "4",
                      "component_id": "63WKbWs5K0ilkujWJQpXEXGD"},
             "connections": [
                 {"name": "utter_sunny", "type": "BOT", "node_id": "5", "component_id": "63gm5BzYuhC1bc6yzysEnN4E"}]
             },
            {"step": {"name": "utter_sunny", "type": "BOT", "node_id": "5",
                      "component_id": "63gm5BzYuhC1bc6yzysEnN4E"},
             "connections": None
             },
            {"step": {"name": "umbrella", "type": "SLOT", "value": 'Yes', "node_id": "6",
                      "component_id": "634a9bwPPj2y3zF5HOVgLiXx"},
             "connections": None
             },
            {"step": {"name": "rainy", "type": "INTENT", "node_id": "3",
                      "component_id": "633w6kSXuz3qqnPU571jZyCv"},
             "connections": [{"name": "umbrella", "type": "SLOT", "value": 'Yes', "node_id": "6",
                              "component_id": "634a9bwPPj2y3zF5HOVgLiXx"}]
             }
        ]
        steps_mf_ten = [
            {"step": {"name": "greet", "type": "INTENT", "node_id": "1", "component_id": "MNbcg"},
             "connections": [{"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "MNbcg"}]
             },
            {"step": {"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "MNbcg"},
             "connections": [{"name": "queries", "type": "INTENT", "node_id": "3", "component_id": "MNbcg"},
                             {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "MNbcg"}]
             },
            {"step": {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "MNbcg"},
             "connections": None
             },
            {"step": {"name": "queries", "type": "INTENT", "node_id": "3", "component_id": "MNbcg"},
             "connections": None
             },
        ]
        steps_mf_eleven = [
            {"step": {"name": "wish", "type": "INTENT", "node_id": "1", "component_id": "637d0j9GD059jEwt2jPnlZ7I"},
             "connections": [
                 {"name": "utter_greet", "type": "BOT", "node_id": "2", "component_id": "63uNJw1QvpQZvIpP07dxnmFU"}]
             },
            {"step": {"name": "utter_greet", "type": "BOT", "node_id": "2",
                      "component_id": "63uNJw1QvpQZvIpP07dxnmFU"},
             "connections": [
                 {"name": "moody", "type": "INTENT", "node_id": "3", "component_id": "633w6kSXuz3qqnPU571jZyCv"},
                 {"name": "foody_act", "type": "INTENT", "node_id": "4",
                  "component_id": "63WKbWs5K0ilkujWJQpXEXGD"}]
             },
            {"step": {"name": "foody_act", "type": "INTENT", "node_id": "4",
                      "component_id": "63WKbWs5K0ilkujWJQpXEXGD"},
             "connections": [
                 {"name": "utter_foody", "type": "BOT", "node_id": "5", "component_id": "63gm5BzYuhC1bc6yzysEnN4E"}]
             },
            {"step": {"name": "utter_foody", "type": "BOT", "node_id": "5",
                      "component_id": "63gm5BzYuhC1bc6yzysEnN4E"},
             "connections": None
             },
            {"step": {"name": "utter_moody", "type": "BOT", "node_id": "6",
                      "component_id": "634a9bwPPj2y3zF5HOVgLiXx"},
             "connections": None
             },
            {"step": {"name": "moody", "type": "INTENT", "node_id": "3",
                      "component_id": "633w6kSXuz3qqnPU571jZyCv"},
             "connections": [{"name": "utter_moody", "type": "BOT", "node_id": "6",
                              "component_id": "634a9bwPPj2y3zF5HOVgLiXx"}]
             }
        ]
        metadata_eleven = [{"node_id": '6', "flow_type": 'RULE'}, {"node_id": "5", "flow_type": 'STORY'}]
        steps_mf_twelve = [
            {"step": {"name": "weather", "type": "INTENT", "node_id": "1", "component_id": "637d0j9GD059jEwt2jPnlZ7I"},
             "connections": [
                 {"name": "utter_weather", "type": "BOT", "node_id": "2", "component_id": "63uNJw1QvpQZvIpP07dxnmFU"}]
             },
            {"step": {"name": "utter_weather", "type": "BOT", "node_id": "2",
                      "component_id": "63uNJw1QvpQZvIpP07dxnmFU"},
             "connections": [
                 {"name": "sunny", "type": "INTENT", "node_id": "3", "component_id": "633w6kSXuz3qqnPU571jZyCv"},
                 {"name": "rainy", "type": "INTENT", "node_id": "4",
                  "component_id": "63WKbWs5K0ilkujWJQpXEXGD"}]
             },
            {"step": {"name": "sunny", "type": "INTENT", "node_id": "4",
                      "component_id": "63WKbWs5K0ilkujWJQpXEXGD"},
             "connections": [
                 {"name": "utter_sunny", "type": "BOT", "node_id": "5", "component_id": "63gm5BzYuhC1bc6yzysEnN4E"}]
             },
            {"step": {"name": "utter_sunny", "type": "BOT", "node_id": "5",
                      "component_id": "63gm5BzYuhC1bc6yzysEnN4E"},
             "connections": None
             },
            {"step": {"name": "utter_rainy", "type": "BOT", "node_id": "6",
                      "component_id": "634a9bwPPj2y3zF5HOVgLiXx"},
             "connections": None
             },
            {"step": {"name": "rainy", "type": "INTENT", "node_id": "3",
                      "component_id": "633w6kSXuz3qqnPU571jZyCv"},
             "connections": [{"name": "utter_rainy", "type": "BOT", "node_id": "6",
                              "component_id": "634a9bwPPj2y3zF5HOVgLiXx"}]
             }
        ]
        metadata_twelve = [{"node_id": '2', "flow_type": "RULE"}, {"node_id": "5", "flow_type": "STORY"}]
        steps_mf_fourteen = [
            {"step": {"name": "greet", "type": "BOT", "node_id": "1", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_time", "type": "BOT", "node_id": "2", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "utter_time", "type": "BOT", "node_id": "2", "component_id": "NKUPKJ"},
             "connections": [{"name": "more_queries", "type": "INTENT", "node_id": "3", "component_id": "NKUPKJ"},
                             {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "goodbye", "type": "INTENT", "node_id": "4", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_goodbye", "type": "BOT", "node_id": "5", "component_id": "NKUPKJ"}]
             },
            {"step": {"name": "utter_goodbye", "type": "BOT", "node_id": "5", "component_id": "NKUPKJ"},
             "connections": None
             },
            {"step": {"name": "utter_more_queries", "type": "BOT", "node_id": "6", "component_id": "NKUPKJ"},
             "connections": None
             },
            {"step": {"name": "more_queries", "type": "INTENT", "node_id": "3", "component_id": "NKUPKJ"},
             "connections": [{"name": "utter_more_queries", "type": "BOT", "node_id": "6", "component_id": "NKUPKJ"}]
             }
        ]
        test_dict = {"multiflow_story": [
            {"block_name": "mf_one", "events": steps_mf_one, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_two", "events": steps_mf_two, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_three", "events": steps_mf_three},
            {"block_name": "mf_four", "events": steps_mf_four, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_five", "events": steps_mf_five, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_six", "events": steps_mf_six, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_seven", "events": steps_mf_seven, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_eight", "events": steps_mf_eight, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_nine", "events": steps_mf_nine, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_ten", "events": steps_mf_ten, "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_eleven", "events": steps_mf_eleven, "metadata": metadata_eleven,
             "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_twelve", "events": steps_mf_twelve, "metadata": metadata_twelve,
             "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_thirteen"},
            {"block_name": "mf_fourteen", "events": steps_mf_fourteen,
             "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            {"block_name": "mf_fourteen", "events": steps_mf_fourteen,
             "metadata": None, "start_checkpoints": ['STORY_START'],
             "end_checkpoints": [], "template_type": 'CUSTOM'},
            [{"block_name": "mf_thirteen"}]]}
        errors, count = TrainingDataValidator.validate_multiflow_stories(test_dict)
        assert len(errors) == 23
        assert count['multiflow_stories'] == 16

    def test_validate_multiflow_stories_empty_content(self):
        test_dict = {'multiflow_story': []}
        assert TrainingDataValidator.validate_multiflow_stories(test_dict)
        assert TrainingDataValidator.validate_multiflow_stories([{}])
