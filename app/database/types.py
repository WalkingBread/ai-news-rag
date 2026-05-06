from sqlalchemy import BigInteger, TypeDecorator

class SignedInt64(TypeDecorator):
    """Converts Python's unsigned 64-bit ints to PostgreSQL's signed BIGINT."""
    impl = BigInteger
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        
        if value > 0x7FFFFFFFFFFFFFFF:
            return value - 0x10000000000000000
        
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        
        if value < 0:
            return value + 0x10000000000000000
        
        return value