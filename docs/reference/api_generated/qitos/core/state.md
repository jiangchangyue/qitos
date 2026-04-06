# `qitos.core.state`

- Module Group: `qitos.core`
- Source: [qitos/core/state.py](https://github.com/Qitor/qitos/blob/main/qitos/core/state.py)

## Quick Jump

- [Classes](#classes)
- [Functions](#functions)
- [Class: `StateMigrationError`](#class-statemigrationerror)
- [Class: `StateMigrationRegistry`](#class-statemigrationregistry)
- [Class: `StateSchema`](#class-stateschema)
- [Class: `StateValidationError`](#class-statevalidationerror)

## Classes

<a id="class-statemigrationerror"></a>
???+ note "Class: `StateMigrationError(self, /, *args, **kwargs)`"
    Raised when state migration fails.

<a id="class-statemigrationregistry"></a>
???+ note "Class: `StateMigrationRegistry(self)`"
    Simple in-process migration graph for state schema versions.

<a id="class-stateschema"></a>
???+ note "Class: `StateSchema(self, schema_version: 'int' = 1, task: 'str' = '', current_step: 'int' = 0, max_steps: 'int' = 10, final_result: 'Optional[str]' = None, stop_reason: 'Optional[str]' = None, metadata: 'Dict[str, Any]' = <factory>, metrics: 'Dict[str, Any]' = <factory>) -> None`"
    Canonical typed state base for AgentModule.

<a id="class-statevalidationerror"></a>
???+ note "Class: `StateValidationError(self, /, *args, **kwargs)`"
    Raised when state validation fails.

## Functions

- _None_

## Source Index

- [qitos/core/state.py](https://github.com/Qitor/qitos/blob/main/qitos/core/state.py)