"""The same telemetry rules, running as an AWS Lambda function."""
import json

from sample_app.telemetry import battery_status, power_kw, reading_errors


def handler(event, context):
    reading = json.loads(event.get("body") or "{}")
    errors = reading_errors(reading)
    if errors:
        return {"statusCode": 400, "body": json.dumps({"errors": errors})}
    return {
        "statusCode": 201,
        "body": json.dumps({
            "unit_id": reading["unit_id"],
            "status": battery_status(reading["state_of_charge"]),
            "power_kw": power_kw(reading["voltage_v"], reading["current_a"]),
        }),
    }
