import json


def handler(request):
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps({"ok": True}, ensure_ascii=False),
    }

