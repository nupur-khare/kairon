from mongoengine import connect
import asyncio

from kairon.test.test_models import ModelTester
connect(host="mongodb://192.168.100.38:27017/conversations")

ModelTester.run_tests_on_model("61bb4fc465fa78066a2d93b6")