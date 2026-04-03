import json
from unittest.mock import MagicMock, patch

from scripts.sync_orchestrator import SyncOrchestrator


def load_mock(filename):
    with open(filename) as f:
        return json.load(f)


@patch("scripts.sync_orchestrator.requests.request")
@patch("scripts.sync_orchestrator.requests.get")
def test_pipeline(mock_get, mock_request):
    # Setup Mocks
    infoblox_data = load_mock("tests/data/mock_infoblox.json")
    servicenow_data = load_mock("tests/data/mock_servicenow.json")
    empty_sn_data = {"result": []}

    # BloxOneClient.fetch_subnets() uses requests.get directly
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: infoblox_data,
        raise_for_status=lambda: None,
    )

    # ServiceNowClient._request() uses requests.request(method, url)
    # Call sequence per subnet:
    #   subnet 1 (10.10.20.0/24): GET → existing record → PATCH
    #   subnet 2 (192.168.50.0/24): GET → no record → POST
    mock_request.side_effect = [
        MagicMock(status_code=200, json=lambda: servicenow_data, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: empty_sn_data, raise_for_status=lambda: None),
        MagicMock(status_code=201, json=lambda: {}, raise_for_status=lambda: None),
    ]

    # Run the Orchestrator
    print("Starting Local Mock Validation...")
    orchestrator = SyncOrchestrator()
    orchestrator.run()

    # Verify Logic: requests.request should have been called with PATCH and POST
    methods = [call.args[0].upper() for call in mock_request.call_args_list if call.args]
    assert "PATCH" in methods, f"Expected PATCH call, got methods: {methods}"
    assert "POST" in methods, f"Expected POST call, got methods: {methods}"
    print("Local Validation Successful: Logic verified.")


if __name__ == "__main__":
    test_pipeline()
