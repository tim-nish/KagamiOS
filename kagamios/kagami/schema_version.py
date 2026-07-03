CURRENT_SCHEMA_REGISTRY_VERSION = 1


class SchemaVersionError(Exception):
    def __init__(self, run_schema_version: int):
        self.run_schema_version = run_schema_version
        if run_schema_version > CURRENT_SCHEMA_REGISTRY_VERSION:
            reason = (
                f"run was written under schema registry v{run_schema_version}, "
                f"newer than the installed v{CURRENT_SCHEMA_REGISTRY_VERSION}"
            )
        else:
            reason = (
                f"run was written under schema registry v{run_schema_version}, "
                f"older than the installed v{CURRENT_SCHEMA_REGISTRY_VERSION}; "
                "run `kagami migrate` to upgrade it"
            )
        super().__init__(reason)


def assert_run_mutable(run_schema_version: int) -> None:
    if run_schema_version != CURRENT_SCHEMA_REGISTRY_VERSION:
        raise SchemaVersionError(run_schema_version)
