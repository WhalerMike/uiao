import json
from unittest.mock import patch, MagicMock
from scripts.sync_orchestrator import SyncOrchestrator


def load_mock(filename):
    with open(filename, 'r') as f:
        return json.load(f)


@patch('requests.get')
@patch('requests.patch')
@patch('requests.post')
def test_pipeline(mock_post, mock_patch, mock_get):
    # Setup Mocks
    infoblox_data = load_mock('tests/data/mock_infoblox.json')
    servicenow_data = load_mock('tests/data/mock_servicenow.json')
    empty_sn_data = {"result": []}

    # Define behavior:
    # First GET = InfoBlox Subnets
    # Subsequent GETs = ServiceNow Lookups (One exists, one doesn't)
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: infoblox_data),
        MagicMock(status_code=200, json=lambda: servicenow_data),
        MagicMock(status_code=200, json=lambda: empty_sn_data)
    ]

    # Run the Orchestrator
    print("Starting Local Mock Validation...")
    orchestrator = SyncOrchestrator()
    orchestrator.run()

    # Verify Logic
    assert mock_patch.called, "The script should have updated the existing record."
    assert mock_post.called, "The script should have created the new record."
    print("Local Validation Successful: Logic verified.")


if __name__ == "__main__":
    test_pipeline()
