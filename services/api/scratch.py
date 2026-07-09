class DummyError:
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

def _is_legacy_empty_uuid_error(exc) -> bool:
    message = str(exc).lower()
    return "invalid input syntax for type uuid" in message and '""' in message

msg = """(sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidTextRepresentationError'>: invalid input syntax for type uuid: ""
[SQL: SELECT ...]"""
print("Result:", _is_legacy_empty_uuid_error(DummyError(msg)))
