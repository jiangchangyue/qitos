# `qitos.core.tool`

- Module Group: `qitos.core`
- Source: [qitos/core/tool.py](https://github.com/Qitor/qitos/blob/main/qitos/core/tool.py)

## Quick Jump

- [Classes](#classes)
- [Functions](#functions)
- [Class: `BaseTool`](#class-basetool)
- [Class: `FunctionTool`](#class-functiontool)
- [Class: `ToolMeta`](#class-toolmeta)
- [Class: `ToolPermission`](#class-toolpermission)
- [Class: `ToolPermissionContext`](#class-toolpermissioncontext)
- [Class: `ToolPermissionDecision`](#class-toolpermissiondecision)
- [Class: `ToolPermissionRule`](#class-toolpermissionrule)
- [Class: `ToolSpec`](#class-toolspec)
- [Class: `ToolValidationResult`](#class-toolvalidationresult)
- [Function: `build_tool_spec`](#function-build-tool-spec)
- [Function: `get_tool_meta`](#function-get-tool-meta)
- [Function: `tool`](#function-tool)

## Classes

<a id="class-basetool"></a>
???+ note "Class: `BaseTool(self, spec: 'ToolSpec')`"
    Base abstraction for callable tools.

<a id="class-functiontool"></a>
???+ note "Class: `FunctionTool(self, func: 'Callable[..., Any]', meta: 'Optional[ToolMeta]' = None)`"
    Tool wrapper around callable functions or bound methods.

<a id="class-toolmeta"></a>
???+ note "Class: `ToolMeta(self, name: 'Optional[str]' = None, description: 'Optional[str]' = None, timeout_s: 'Optional[float]' = None, max_retries: 'int' = 0, permissions: 'ToolPermission' = <factory>, required_ops: 'List[str]' = <factory>, input_schema: 'Optional[Dict[str, Any]]' = None, output_schema: 'Optional[Dict[str, Any]]' = None, read_only: 'bool' = False, concurrency_safe: 'bool' = False, requires_user_interaction: 'bool' = False, supports_background: 'bool' = False, result_max_chars: 'Optional[int]' = None, produces_artifact: 'bool' = False, rule_scope_builder: 'Optional[Callable[[Dict[str, Any]], Optional[str]]]' = None) -> None`"
    ToolMeta(name: 'Optional[str]' = None, description: 'Optional[str]' = None, timeout_s: 'Optional[float]' = None, max_retries: 'int' = 0, permissions: 'ToolPermission' = <factory>, required_ops: 'List[str]' = <factory>, input_schema: 'Optional[Dict[str, Any]]' = None, output_schema: 'Optional[Dict[str, Any]]' = None, read_only: 'bool' = False, concurrency_safe: 'bool' = False, requires_user_interaction: 'bool' = False, supports_background: 'bool' = False, result_max_chars: 'Optional[int]' = None, produces_artifact: 'bool' = False, rule_scope_builder: 'Optional[Callable[[Dict[str, Any]], Optional[str]]]' = None)

<a id="class-toolpermission"></a>
???+ note "Class: `ToolPermission(self, filesystem_read: 'bool' = False, filesystem_write: 'bool' = False, network: 'bool' = False, command: 'bool' = False) -> None`"
    ToolPermission(filesystem_read: 'bool' = False, filesystem_write: 'bool' = False, network: 'bool' = False, command: 'bool' = False)

<a id="class-toolpermissioncontext"></a>
???+ note "Class: `ToolPermissionContext(self, allow_rules: 'List[ToolPermissionRule]' = <factory>, deny_rules: 'List[ToolPermissionRule]' = <factory>, ask_rules: 'List[ToolPermissionRule]' = <factory>, default_decision: 'str' = 'allow') -> None`"
    ToolPermissionContext(allow_rules: 'List[ToolPermissionRule]' = <factory>, deny_rules: 'List[ToolPermissionRule]' = <factory>, ask_rules: 'List[ToolPermissionRule]' = <factory>, default_decision: 'str' = 'allow')

<a id="class-toolpermissiondecision"></a>
???+ note "Class: `ToolPermissionDecision(self, decision: 'str', message: 'str' = '', scope: 'str' = '', matched_rule: 'Optional[ToolPermissionRule]' = None, updated_args: 'Optional[Dict[str, Any]]' = None) -> None`"
    ToolPermissionDecision(decision: 'str', message: 'str' = '', scope: 'str' = '', matched_rule: 'Optional[ToolPermissionRule]' = None, updated_args: 'Optional[Dict[str, Any]]' = None)

<a id="class-toolpermissionrule"></a>
???+ note "Class: `ToolPermissionRule(self, effect: 'str', tool_name: 'str' = '', tool_family: 'str' = '', scope: 'str' = '', message: 'str' = '') -> None`"
    ToolPermissionRule(effect: 'str', tool_name: 'str' = '', tool_family: 'str' = '', scope: 'str' = '', message: 'str' = '')

<a id="class-toolspec"></a>
???+ note "Class: `ToolSpec(self, name: 'str', description: 'str', parameters: 'Dict[str, Dict[str, Any]]' = <factory>, required: 'List[str]' = <factory>, timeout_s: 'Optional[float]' = None, max_retries: 'int' = 0, permissions: 'ToolPermission' = <factory>, required_ops: 'List[str]' = <factory>, input_schema: 'Optional[Dict[str, Any]]' = None, output_schema: 'Optional[Dict[str, Any]]' = None, read_only: 'bool' = False, concurrency_safe: 'bool' = False, requires_user_interaction: 'bool' = False, supports_background: 'bool' = False, result_max_chars: 'Optional[int]' = None, produces_artifact: 'bool' = False, rule_scope_builder: 'Optional[Callable[[Dict[str, Any]], Optional[str]]]' = None) -> None`"
    ToolSpec(name: 'str', description: 'str', parameters: 'Dict[str, Dict[str, Any]]' = <factory>, required: 'List[str]' = <factory>, timeout_s: 'Optional[float]' = None, max_retries: 'int' = 0, permissions: 'ToolPermission' = <factory>, required_ops: 'List[str]' = <factory>, input_schema: 'Optional[Dict[str, Any]]' = None, output_schema: 'Optional[Dict[str, Any]]' = None, read_only: 'bool' = False, concurrency_safe: 'bool' = False, requires_user_interaction: 'bool' = False, supports_background: 'bool' = False, result_max_chars: 'Optional[int]' = None, produces_artifact: 'bool' = False, rule_scope_builder: 'Optional[Callable[[Dict[str, Any]], Optional[str]]]' = None)

<a id="class-toolvalidationresult"></a>
???+ note "Class: `ToolValidationResult(self, valid: 'bool' = True, message: 'str' = '', code: 'str' = '', suggested_args: 'Optional[Dict[str, Any]]' = None) -> None`"
    ToolValidationResult(valid: 'bool' = True, message: 'str' = '', code: 'str' = '', suggested_args: 'Optional[Dict[str, Any]]' = None)

## Functions

<a id="function-build-tool-spec"></a>
???+ note "Function: `build_tool_spec(func: 'Callable[..., Any]', meta: 'ToolMeta') -> 'ToolSpec'`"
    _No summary available._

<a id="function-get-tool-meta"></a>
???+ note "Function: `get_tool_meta(func: 'Callable[..., Any]') -> 'Optional[ToolMeta]'`"
    _No summary available._

<a id="function-tool"></a>
???+ note "Function: `tool(name: 'Optional[str]' = None, description: 'Optional[str]' = None, timeout_s: 'Optional[float]' = None, max_retries: 'int' = 0, permissions: 'Optional[ToolPermission]' = None, required_ops: 'Optional[List[str]]' = None, input_schema: 'Optional[Dict[str, Any]]' = None, output_schema: 'Optional[Dict[str, Any]]' = None, read_only: 'bool' = False, concurrency_safe: 'bool' = False, requires_user_interaction: 'bool' = False, supports_background: 'bool' = False, result_max_chars: 'Optional[int]' = None, produces_artifact: 'bool' = False, rule_scope_builder: 'Optional[Callable[[Dict[str, Any]], Optional[str]]]' = None)`"
    Decorator that marks a callable as a QitOS tool without changing binding semantics.

## Source Index

- [qitos/core/tool.py](https://github.com/Qitor/qitos/blob/main/qitos/core/tool.py)
