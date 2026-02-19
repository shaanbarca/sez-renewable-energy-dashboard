from os import getenv


class Config:
    # Project-level settings
    MODEL = getenv("APP_REF", "SIQ")


    # External tokens / secrets
    MAPBOX_TOKEN = getenv("MAPBOX_TOKEN", "")
    S3_ACCESS_KEY = getenv("S3_ACCESS_KEY", "")
    S3_SECRET_ACCESS_KEY = getenv("S3_SECRET_ACCESS_KEY", "")
