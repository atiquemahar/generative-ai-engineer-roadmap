# Day 03 Prompt Comparison Findings

## Pass Rates

- **v1_basic**: 9/20 passed, avg latency 4.72s
- **v2_structured**: 19/20 passed, avg latency 4.96s
- **v3_fewshot**: 19/20 passed, avg latency 3.98s

## Failures

- [v1_basic] Input 3: Error code: 400 - {'error': {'message': 'The response was filtered due to the prompt triggering Azure OpenAI�s content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766', 'type': 'invalid_request_error', 'param': 'prompt', 'code': 'content_filter', 'content_filters': [{'blocked': True, 'source_type': 'prompt', 'content_filter_raw': [], 'content_filter_results': {'jailbreak': {'detected': True, 'filtered': True}, 'hate': {'filtered': False, 'severity': 'safe'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}, 'self_harm': {'filtered': False, 'severity': 'safe'}}, 'content_filter_offsets': {'start_offset': 0, 'end_offset': 1519, 'check_offset': 0}}], 'innererror': {'code': 'ContentFiltered'}}}
- [v1_basic] Input 4: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 5: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 8: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 9: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 10: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 11: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 14: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 15: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 16: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v1_basic] Input 19: 1 validation error for Complaint
requested_action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/string_type
- [v2_structured] Input 3: Error code: 400 - {'error': {'message': 'The response was filtered due to the prompt triggering Azure OpenAI�s content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766', 'type': 'invalid_request_error', 'param': 'prompt', 'code': 'content_filter', 'content_filters': [{'blocked': True, 'source_type': 'prompt', 'content_filter_raw': [], 'content_filter_results': {'hate': {'filtered': False, 'severity': 'safe'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}, 'self_harm': {'filtered': False, 'severity': 'safe'}, 'jailbreak': {'detected': True, 'filtered': True}}, 'content_filter_offsets': {'start_offset': 0, 'end_offset': 1519, 'check_offset': 0}}], 'innererror': {'code': 'ContentFiltered'}}}
- [v3_fewshot] Input 3: Error code: 400 - {'error': {'message': 'The response was filtered due to the prompt triggering Azure OpenAI�s content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766', 'type': 'invalid_request_error', 'param': 'prompt', 'code': 'content_filter', 'content_filters': [{'blocked': True, 'source_type': 'prompt', 'content_filter_raw': [], 'content_filter_results': {'jailbreak': {'detected': True, 'filtered': True}, 'hate': {'filtered': False, 'severity': 'safe'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}, 'self_harm': {'filtered': False, 'severity': 'safe'}}, 'content_filter_offsets': {'start_offset': 0, 'end_offset': 1519, 'check_offset': 0}}], 'innererror': {'code': 'ContentFiltered'}}}

## Observations

v1_basic fails 11 times:
input_3 fails due to Azure OpenAI content safety filter not prompt failure
all other failures are pydantic validation error for requested_action as it is mentioned in the prompt but it does not explicitly describe what requested_action is.

In first run , v2_structured prompt and v3_fewshot prompt failed 5 times, one for input_3: Azure OpenAI content safety filter for prompt injection.
Rest of the failures are the caused by pydantic validation errorr: Shipment_delay was written instead of shipment_delay, so LLM model was following the instruction and returned the output as Shipment_delay (Capital S) which caused pydantic valiadtion as it is written shipment_delay in pydantic model.

In second run when I fixed the prompt wrote the shipment_delay with small letter and add pydantic validator which normalizes capital letter to lowercase — 'Shipment_delay' → 'shipment_delay'. 
Result changed 19 input passed only one failed which is input_3.

v2_structured prompt and fewshot prompt both provide same result 19/20 passed 
but when considering latency, v3_fewshot has lower latency (3.98s vs 4.96s) because few-shot examples give the model concrete output patterns to follow, so it reasons less internally and responds faster. 
v3 costs more input tokens because the prompt is longer, but saves latency end-to-end.

In production I would use v3_fewshot because the latency advantage compounds across thousands of calls, and the extra input token cost is fixed and predictable regardless of input complexity. v2_structured remains a valid choice if prompt length is a concern or if the system prompt context window is already large.