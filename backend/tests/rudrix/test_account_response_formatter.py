from app.ai.account_response_formatter import format_account_investigation_result


def test_formats_single_account_without_internal_tool_language():
    message = format_account_investigation_result(
        {
            "count": 1,
            "items": [
                {
                    "displayName": "Aditya Sinha",
                    "application": "Active Directory",
                    "username": "asinha",
                    "email": "asinha@examplecorp.com",
                    "employeeId": "W00003",
                    "nativeIdentity": "02ebc443-12b6-5a1e-bbca-073c9b0f7879",
                    "accountStatus": "ACTIVE",
                    "orphaned": False,
                }
            ],
        }
    )

    assert "Aditya Sinha" in message
    assert "W00003" in message
    assert "Orphaned: No" in message
    assert "tool call" not in message.lower()
    assert "original user question" not in message.lower()


def test_formats_empty_result_message():
    message = format_account_investigation_result(
        {
            "count": 0,
            "items": [],
            "message": "No matching active accounts were found.",
        }
    )

    assert message == "No matching active accounts were found."
