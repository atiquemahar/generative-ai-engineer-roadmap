# Day 02 Extractor - result improvement report and debugging

## Run 1 

errror: 'method' object does not support the context manager protocol

## fix
get_openai_client missing () rewritten as get_openai_client()

## Run 2 

14 passed form 20 input test
pass rate : 14/20 (70%)

1. LLM model was returning confidence score in float
Pydantic model was set for string with "high", "medium" and "low" confidence score

### fix
field_validator normalizes the float value into string by defining the function normalize_confidence

2. Empty responses on valid inputs
sending 20 API calls in a tight loop with no delay. Azure throttles and returns empty bodies silently. 

## Fix: 
add time.sleep(1) between calls.

3. Unterminated string
LLM Model was hitting token limit truncating the response in the middle

## Fix: 
increased token limit to 800 tokens.

## Run 3
All 20/20 test input passed
extracted the  structured fields  defined in pydantic model.

