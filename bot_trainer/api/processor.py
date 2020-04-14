from bot_trainer.api.data_objects import *
from bot_trainer.utils import Utility
from mongoengine.errors import DoesNotExist


class AccountProcessor:
    @staticmethod
    def add_account(name: str, user: str):
        Utility.is_exist(
            Account, query={"name": name}, exp_message="Account name already exists!"
        )
        return Account(name=name, user=user).save().to_mongo().to_dict()

    @staticmethod
    def get_account(account: int):
        return Account.objects(status=True).get(id=account).to_mongo().to_dict()

    @staticmethod
    def add_bot(name: str, account: int, user: str):
        Utility.is_exist(
            Bot, query={"name": name}, exp_message="Account name already exists!"
        )
        return Bot(name=name, account=account, user=user).save().to_mongo().to_dict()

    @staticmethod
    def get_bot(name: str):
        return Bot.objects(status=True).get(name=name).to_mongo().to_dict()

    @staticmethod
    def add_user(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        account: int,
        bot: str,
        user: str,
    ):
        Utility.is_exist(
            User,
            query={"email": email},
            exp_message="User already exists! try with different email address.",
        )
        return (
            User(
                email=email,
                password=Utility.get_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                account=account,
                bot=bot,
                user=user,
            )
            .save()
            .to_mongo()
            .to_dict()
        )

    @staticmethod
    def get_user(email: str):
        try:
            return User.objects(status=True).get(email=email).to_mongo().to_dict()
        except:
            raise DoesNotExist("User does not exists!")

    @staticmethod
    def get_user_details(email: str):
        user = AccountProcessor.get_user(email)
        if not user["status"]:
            raise ValidationError("Inactive User please contact admin!")
        bot = AccountProcessor.get_bot(user["bot"])
        account = AccountProcessor.get_account(user["account"])
        if not bot["status"]:
            raise ValidationError("Inactive Bot Please contact system admin!")
        if not account["status"]:
            raise ValidationError("Inactive Account Please contact system admin!")
        return user
