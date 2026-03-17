import json


def handler(request):
    """
    Vercel Python Serverless Function entrypoint.
    Note: project ini bot long-running, jadi endpoint ini hanya untuk health/info.
    """
    body = {
        "ok": True,
        "service": "molty-bot-KBG",
        "note": "This is a serverless health endpoint. The bot (main.py) is a long-running process and is not executed on Vercel.",
        "endpoints": ["/health"],
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }

