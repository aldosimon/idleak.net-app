import lambda_function as lambda_module
import json
import logging

# Set up basic console logging to see the output from your lambda's logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def main():
    # 1. Define a mock event and context (they are usually empty for simple scheduled jobs)
    mock_event = {}
    mock_context = {}

    logger.info("--- Starting Local Lambda Test ---")

    # 2. Call the main lambda handler function
    response = lambda_module.lambda_handler(mock_event, mock_context)

    # 3. Print the result
    logger.info("--- Lambda Handler Response ---")
    print(json.dumps(response, indent=4))
    logger.info("---------------------------------")

if __name__ == "__main__":
    main()