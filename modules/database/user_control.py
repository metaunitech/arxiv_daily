from modules.models.database import SingletonDatabase
from modules.database.db_models import UserDetails
from modules.models.entity_models import UserType, Entity
from loguru import logger
from pathlib import Path
from datetime import datetime, timedelta


class UserControlException(Exception):
    pass


class UserControl(SingletonDatabase):
    """
    Inheriting from SingletonDatabase.
    """

    def __init__(self, db_config_path: Path):
        super().__init__(db_config_path)

    def register_user(self, user_type: str, user_type_duration_seconds: int, platform: str, user_platform_id: str,
                      user_platform_name: str, entity: str):
        if user_type not in UserType.__members__:
            raise UserControlException(f"{user_type} not in UserType Models")

        if entity not in Entity.__members__:
            raise UserControlException(f"{entity} not in Entity Models")

        with self.session as session:
            # Create a new UserDetails object
            user_type_start_ts = datetime.now()
            if not user_type_duration_seconds:
                time_delta = UserType[user_type].Duration
                if time_delta == -1:
                    user_type_end_ts = datetime.max
                else:
                    user_type_end_ts = user_type_start_ts + timedelta(seconds=time_delta)
            user_details = UserDetails(
                entity = entity,
                user_type=user_type,
                user_type_start_ts=user_type_start_ts,
                user_type_end_ts=user_type_end_ts,
                platform=platform,
                user_platform_id=user_platform_id,
                user_platform_name=user_platform_name
            )
            session.add(user_details)
            session.commit()
            logger.success(f"Added {str(user_details)}")

    def block_user(self, user_platform_id, platform: str):
        with self.session as session:
            # Retrieve the user details based on user_platform_id and platform
            user_details = session.query(UserDetails).filter_by(user_platform_id=user_platform_id,
                                                                platform=platform).first()

            # Update the is_banned attribute of the user details
            user_details.is_banned = True

            # Commit the changes
            session.commit()

    def set_user_type(self, user_platform_id, platform: str, user_type: str, duration_s: int):
        with self.session as session:
            # Retrieve the user details based on user_platform_id and platform
            user_details = session.query(UserDetails).filter_by(user_platform_id=user_platform_id,
                                                                platform=platform).first()

            # Update the user_type and user_type_end_ts attributes of the user details
            user_details.user_type = user_type
            user_details.user_type_end_ts = datetime.now() + timedelta(seconds=duration_s)

            # Commit the changes
            session.commit()

    def get_user_details(self, user_platform_id=None, platform=None, user_idx=None):
        with self.session as session:
            if user_idx:
                # Retrieve user details based on user_idx
                user_details = session.query(UserDetails).filter_by(idx=user_idx).first()
            elif user_platform_id and platform:
                # Retrieve user details based on user_platform_id and platform
                user_details = session.query(UserDetails).filter_by(user_platform_id=user_platform_id,
                                                                    platform=platform).first()
            else:
                raise UserControlException("You need to provide either (user_platform_id&platform) or user_idx")

            return user_details

    def register_user_message(self, user_idx, ):
        pass