from enum import Enum


class Entity(Enum):
    Administrator = 0
    GroupChat = 1
    User = 2


Entity.Administrator.entity_type = 'Administrator'
Entity.GroupChat.entity_type = 'GroupChat'
Entity.User.entity_type = 'User'


class UserType(Enum):
    Administrator = 0
    NormalUser = 1
    PaidUser = 2


UserType.Administrator.Duration = -1
UserType.NormalUser.Duration = -1
UserType.PaidUser.Duration = 86400 * 30

if __name__ == "__main__":
    print("HRE")
