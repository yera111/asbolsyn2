# As Bolsyn Testing Scripts

This directory contains scripts for testing and validating the As Bolsyn Telegram bot.

## Available Scripts

### End-to-End Testing

- **`e2e_test.py`**: A comprehensive end-to-end testing script that guides you through testing all major features of the As Bolsyn bot in a structured way.

    ```bash
    python e2e_test.py
    ```

    This script will:
    - Guide you through each test step
    - Record the results of each step
    - Generate a detailed log file
    - Provide a summary of test results

### Test Setup

- **`setup_test_data.py`**: A script to help you set up test data and accounts for end-to-end testing.

    ```bash
    python setup_test_data.py
    ```

    This script will:
    - Create or update a test configuration file
    - Prompt for test account details
    - Configure test payment credentials
    - Set up test location data for Almaty
    - Generate a test guide based on your configuration

## Usage Workflow

1. First, run `setup_test_data.py` to configure your test environment
2. Use the generated configuration to set up necessary test accounts
3. Run `e2e_test.py` to perform comprehensive testing
4. Review the generated logs and results
5. Update the test configuration as needed for future tests

## Logs and Outputs

- **Test Configuration**: Saved in `test_config.json` and `e2e_test_config.json`
- **Test Setup Logs**: Saved in `test_setup_YYYYMMDD_HHMMSS.log`
- **Test Results Logs**: Saved in `e2e_test_results_YYYYMMDD_HHMMSS.log`

## Documentation

For more details on the testing process, refer to:

- `docs/e2e_testing_guide.md`: Comprehensive guide to end-to-end testing
- `docs/sample_test_results.md`: Example of what test results should look like 