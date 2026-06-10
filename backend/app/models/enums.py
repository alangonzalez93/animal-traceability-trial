import enum


class AnimalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEAD = "DEAD"
    SOLD = "SOLD"


class AnimalCategory(str, enum.Enum):
    CALF = "CALF"
    STEER = "STEER"
    COW = "COW"
    BULL = "BULL"
    HEIFER = "HEIFER"


class Breed(str, enum.Enum):
    ANGUS = "ANGUS"
    HEREFORD = "HEREFORD"
    BRAHMAN = "BRAHMAN"
    LIMOUSIN = "LIMOUSIN"
    SHORTHORN = "SHORTHORN"
    CRIOLLO = "CRIOLLO"


class EventType(str, enum.Enum):
    BIRTH = "BIRTH"
    MOVE = "MOVE"
    DEATH = "DEATH"
    SALE = "SALE"
    RECLASSIFICATION = "RECLASSIFICATION"
    WEIGHT = "WEIGHT"
    VACCINATION = "VACCINATION"
