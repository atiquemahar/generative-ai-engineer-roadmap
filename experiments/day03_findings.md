# Day 03 Prompt Comparison Findings

## Pass Rates

- **v1_basic**: 10/20 passed, avg latency 5.05s
- **v2_structured**: 15/20 passed, avg latency 4.45s
- **v3_fewshot**: 15/20 passed, avg latency 4.72s

## Failures

- [v1_basic] Input 3: Error code: 400 - {'error': {'message': 'The response was filtered due to the prompt triggering Azure OpenAI’s content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766', 'type': 'invalid_request_error', 'param': 'prompt', 'code': 'content_filter', 'content_filters': [{'blocked': True, 'source_type': 'prompt', 'content_filter_raw': [], 'content_filter_results': {'jailbreak': {'detected': True, 'filtered': True}, 'hate': {'filtered': False, 'severity': 'safe'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}, 'self_harm': {'filtered': False, 'severity': 'safe'}}, 'content_filter_offsets': {'start_offset': 0, 'end_offset': 1519, 'check_offset': 0}}], 'innererror': {'code': 'ContentFiltered'}}}
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
- [v2_structured] Input 0: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v2_structured] Input 2: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v2_structured] Input 3: Error code: 400 - {'error': {'message': 'The response was filtered due to the prompt triggering Azure OpenAI’s content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766', 'type': 'invalid_request_error', 'param': 'prompt', 'code': 'content_filter', 'content_filters': [{'blocked': True, 'source_type': 'prompt', 'content_filter_raw': [], 'content_filter_results': {'hate': {'filtered': False, 'severity': 'safe'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}, 'self_harm': {'filtered': False, 'severity': 'safe'}, 'jailbreak': {'detected': True, 'filtered': True}}, 'content_filter_offsets': {'start_offset': 0, 'end_offset': 1519, 'check_offset': 0}}], 'innererror': {'code': 'ContentFiltered'}}}
- [v2_structured] Input 6: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v2_structured] Input 11: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v3_fewshot] Input 0: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v3_fewshot] Input 2: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v3_fewshot] Input 3: Error code: 400 - {'error': {'message': 'The response was filtered due to the prompt triggering Azure OpenAI’s content management policy. Please modify your prompt and retry. To learn more about our content filtering policies please read our documentation: https://go.microsoft.com/fwlink/?linkid=2198766', 'type': 'invalid_request_error', 'param': 'prompt', 'code': 'content_filter', 'content_filters': [{'blocked': True, 'source_type': 'prompt', 'content_filter_raw': [], 'content_filter_results': {'hate': {'filtered': False, 'severity': 'safe'}, 'sexual': {'filtered': False, 'severity': 'safe'}, 'violence': {'filtered': False, 'severity': 'safe'}, 'self_harm': {'filtered': False, 'severity': 'safe'}, 'jailbreak': {'detected': True, 'filtered': True}}, 'content_filter_offsets': {'start_offset': 0, 'end_offset': 1519, 'check_offset': 0}}], 'innererror': {'code': 'ContentFiltered'}}}
- [v3_fewshot] Input 6: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error
- [v3_fewshot] Input 11: 1 validation error for Complaint
intent
  Input should be 'shipment_delay', 'refund_request', 'product_defect', 'account_issue' or 'general_inquiry' [type=literal_error, input_value='Shipment_delay', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error

## Observations

(Write your own observations here after reviewing the CSV)
