import unittest

class TestJitter(unittest.TestCase):

    def test_jiter(self):

        #test imported from crates/jiter-python/tests/test_jiter.py
        from concurrent.futures import ThreadPoolExecutor
        import json
        from decimal import Decimal
        from pathlib import Path
        from typing import Any

        import jiter
        import pytest
        from math import inf
        # from dirty_equals import IsFloatNan

        JITER_BENCH_DIR = Path(__file__).parent / 'benches'

        JITER_BENCH_DATAS = [
            (JITER_BENCH_DIR / 'bigints_array.json').read_bytes(),
            (JITER_BENCH_DIR / 'floats_array.json').read_bytes(),
            (JITER_BENCH_DIR / 'massive_ints_array.json').read_bytes(),
            (JITER_BENCH_DIR / 'medium_response.json').read_bytes(),
            (JITER_BENCH_DIR / 'pass1.json').read_bytes(),
            (JITER_BENCH_DIR / 'pass2.json').read_bytes(),
            (JITER_BENCH_DIR / 'sentence.json').read_bytes(),
            (JITER_BENCH_DIR / 'short_numbers.json').read_bytes(),
            (JITER_BENCH_DIR / 'string_array_unique.json').read_bytes(),
            (JITER_BENCH_DIR / 'string_array.json').read_bytes(),
            (JITER_BENCH_DIR / 'true_array.json').read_bytes(),
            (JITER_BENCH_DIR / 'true_object.json').read_bytes(),
            (JITER_BENCH_DIR / 'unicode.json').read_bytes(),
            (JITER_BENCH_DIR / 'x100.json').read_bytes(),
        ]


        def test_python_parse_numeric():
            parsed = jiter.from_json(
                b'  { "int": 1, "bigint": 123456789012345678901234567890, "float": 1.2}  '
            )
            assert parsed == {'int': 1, 'bigint': 123456789012345678901234567890, 'float': 1.2}


        # def test_python_parse_other_cached():
        #     parsed = jiter.from_json(
        #         b'["string", true, false, null, NaN, Infinity, -Infinity]',
        #         allow_inf_nan=True,
        #         cache_mode=True,
        #     )
        #     assert parsed == ['string', True, False, None, IsFloatNan(), inf, -inf]


        def test_python_parse_other_no_cache():
            parsed = jiter.from_json(
                b'["string", true, false, null]',
                cache_mode=False,
            )
            assert parsed == ['string', True, False, None]


        def test_python_disallow_nan():
            with pytest.raises(ValueError, match='expected value at line 1 column 2'):
                jiter.from_json(b'[NaN]', allow_inf_nan=False)


        def test_error():
            with pytest.raises(ValueError, match='EOF while parsing a list at line 1 column 9'):
                jiter.from_json(b'["string"')


        def test_recursion_limit():
            with pytest.raises(
                ValueError, match='recursion limit exceeded at line 1 column 202'
            ):
                jiter.from_json(b'[' * 10_000)


        def test_recursion_limit_incr():
            json = b'[' + b', '.join(b'[1]' for _ in range(2000)) + b']'
            v = jiter.from_json(json)
            assert len(v) == 2000

            v = jiter.from_json(json)
            assert len(v) == 2000


        def test_extracted_value_error():
            with pytest.raises(ValueError, match='expected value at line 1 column 1'):
                jiter.from_json(b'xx')


        def test_partial_array():
            json = b'["string", true, null, 1, "foo'

            with pytest.raises(
                ValueError, match='EOF while parsing a string at line 1 column 30'
            ):
                jiter.from_json(json, partial_mode=False)

            parsed = jiter.from_json(json, partial_mode=True)
            assert parsed == ['string', True, None, 1]

            # test that stopping at every points is ok
            for i in range(1, len(json)):
                parsed = jiter.from_json(json[:i], partial_mode=True)
                assert isinstance(parsed, list)


        def test_partial_array_trailing_strings():
            json = b'["string", true, null, 1, "foo'
            parsed = jiter.from_json(json, partial_mode='trailing-strings')
            assert parsed == ['string', True, None, 1, 'foo']

            # test that stopping at every points is ok
            for i in range(1, len(json)):
                parsed = jiter.from_json(json[:i], partial_mode='trailing-strings')
                assert isinstance(parsed, list)


        def test_partial_array_first():
            json = b'['
            parsed = jiter.from_json(json, partial_mode=True)
            assert parsed == []

            with pytest.raises(ValueError, match='EOF while parsing a list at line 1 column 1'):
                jiter.from_json(json)

            with pytest.raises(ValueError, match='EOF while parsing a list at line 1 column 1'):
                jiter.from_json(json, partial_mode='off')


        def test_partial_object():
            json = b'{"a": 1, "b": 2, "c'
            parsed = jiter.from_json(json, partial_mode=True)
            assert parsed == {'a': 1, 'b': 2}

            # test that stopping at every points is ok
            for i in range(1, len(json)):
                parsed = jiter.from_json(json, partial_mode=True)
                assert isinstance(parsed, dict)


        def test_partial_object_string():
            json = b'{"a": 1, "b": 2, "c": "foo'
            parsed = jiter.from_json(json, partial_mode=True)
            assert parsed == {'a': 1, 'b': 2}
            parsed = jiter.from_json(json, partial_mode='on')
            assert parsed == {'a': 1, 'b': 2}

            # test that stopping at every points is ok
            for i in range(1, len(json)):
                parsed = jiter.from_json(json, partial_mode=True)
                assert isinstance(parsed, dict)

            json = b'{"title": "Pride and Prejudice", "author": "Jane A'
            parsed = jiter.from_json(json, partial_mode=True)
            assert parsed == {'title': 'Pride and Prejudice'}


        def test_partial_object_string_trailing_strings():
            json = b'{"a": 1, "b": 2, "c": "foo'
            parsed = jiter.from_json(json, partial_mode='trailing-strings')
            assert parsed == {'a': 1, 'b': 2, 'c': 'foo'}

            # test that stopping at every points is ok
            for i in range(1, len(json)):
                parsed = jiter.from_json(json, partial_mode=True)
                assert isinstance(parsed, dict)

            json = b'{"title": "Pride and Prejudice", "author": "Jane A'
            parsed = jiter.from_json(json, partial_mode='trailing-strings')
            assert parsed == {'title': 'Pride and Prejudice', 'author': 'Jane A'}


        def test_partial_nested():
            json = b'{"a": 1, "b": 2, "c": [1, 2, {"d": 1, '
            parsed = jiter.from_json(json, partial_mode=True)
            assert parsed == {'a': 1, 'b': 2, 'c': [1, 2, {'d': 1}]}

            # test that stopping at every points is ok
            for i in range(1, len(json)):
                parsed = jiter.from_json(json[:i], partial_mode=True)
                assert isinstance(parsed, dict)


        def test_partial_error():
            json = b'["string", true, null, 1, "foo'

            with pytest.raises(
                ValueError, match='EOF while parsing a string at line 1 column 30'
            ):
                jiter.from_json(json, partial_mode=False)

            assert jiter.from_json(json, partial_mode=True) == ['string', True, None, 1]

            msg = "Invalid partial mode, should be `'off'`, `'on'`, `'trailing-strings'` or a `bool`"
            with pytest.raises(ValueError, match=msg):
                jiter.from_json(json, partial_mode='wrong')
            with pytest.raises(TypeError, match=msg):
                jiter.from_json(json, partial_mode=123)


        def test_python_cache_usage_all():
            jiter.cache_clear()
            parsed = jiter.from_json(b'{"foo": "bar", "spam": 3}', cache_mode='all')
            assert parsed == {'foo': 'bar', 'spam': 3}
            assert jiter.cache_usage() == 3


        def test_python_cache_usage_keys():
            jiter.cache_clear()
            parsed = jiter.from_json(b'{"foo": "bar", "spam": 3}', cache_mode='keys')
            assert parsed == {'foo': 'bar', 'spam': 3}
            assert jiter.cache_usage() == 2


        def test_python_cache_usage_none():
            jiter.cache_clear()
            parsed = jiter.from_json(
                b'{"foo": "bar", "spam": 3}',
                cache_mode='none',
            )
            assert parsed == {'foo': 'bar', 'spam': 3}
            assert jiter.cache_usage() == 0


        def test_use_tape():
            json = '  "foo\\nbar"  '.encode()
            jiter.cache_clear()
            parsed = jiter.from_json(json, cache_mode=False)
            assert parsed == 'foo\nbar'


        def test_unicode():
            json = '{"💩": "£"}'.encode()
            jiter.cache_clear()
            parsed = jiter.from_json(json, cache_mode=False)
            assert parsed == {'💩': '£'}


        def test_unicode_cache():
            json = '{"💩": "£"}'.encode()
            jiter.cache_clear()
            parsed = jiter.from_json(json)
            assert parsed == {'💩': '£'}


        def test_json_float():
            f = jiter.LosslessFloat(b'123.45')
            assert str(f) == '123.45'
            assert repr(f) == 'LosslessFloat(123.45)'
            assert float(f) == 123.45
            assert f.as_decimal() == Decimal('123.45')
            assert bytes(f) == b'123.45'


        def test_json_float_scientific():
            f = jiter.LosslessFloat(b'123e4')
            assert str(f) == '123e4'
            assert float(f) == 123e4
            assert f.as_decimal() == Decimal('123e4')


        def test_json_float_invalid():
            with pytest.raises(ValueError, match='trailing characters at line 1 column 6'):
                jiter.LosslessFloat(b'123.4x')


        def test_lossless_floats():
            f = jiter.from_json(b'12.3')
            assert isinstance(f, float)
            assert f == 12.3

            f = jiter.from_json(b'12.3', float_mode='float')
            assert isinstance(f, float)
            assert f == 12.3

            f = jiter.from_json(b'12.3', float_mode='lossless-float')
            assert isinstance(f, jiter.LosslessFloat)
            assert str(f) == '12.3'
            assert float(f) == 12.3
            assert f.as_decimal() == Decimal('12.3')

            f = jiter.from_json(b'123.456789123456789e45', float_mode='lossless-float')
            assert isinstance(f, jiter.LosslessFloat)
            assert 123e45 < float(f) < 124e45
            assert f.as_decimal() == Decimal('1.23456789123456789E+47')
            assert bytes(f) == b'123.456789123456789e45'
            assert str(f) == '123.456789123456789e45'
            assert repr(f) == 'LosslessFloat(123.456789123456789e45)'

            f = jiter.from_json(b'123', float_mode='lossless-float')
            assert isinstance(f, int)
            assert f == 123

            with pytest.raises(ValueError, match='expected value at line 1 column 1'):
                jiter.from_json(b'wrong', float_mode='lossless-float')

            with pytest.raises(ValueError, match='trailing characters at line 1 column 2'):
                jiter.from_json(b'1wrong', float_mode='lossless-float')


        def test_decimal_floats():
            f = jiter.from_json(b'12.3')
            assert isinstance(f, float)
            assert f == 12.3

            f = jiter.from_json(b'12.3', float_mode='decimal')
            assert isinstance(f, Decimal)
            assert f == Decimal('12.3')

            f = jiter.from_json(b'123.456789123456789e45', float_mode='decimal')
            assert isinstance(f, Decimal)
            assert f == Decimal('1.23456789123456789E+47')

            f = jiter.from_json(b'123', float_mode='decimal')
            assert isinstance(f, int)
            assert f == 123

            with pytest.raises(ValueError, match='expected value at line 1 column 1'):
                jiter.from_json(b'wrong', float_mode='decimal')

            with pytest.raises(ValueError, match='trailing characters at line 1 column 2'):
                jiter.from_json(b'1wrong', float_mode='decimal')


        def test_unicode_roundtrip():
            original = ['中文']
            json_data = json.dumps(original).encode()
            assert jiter.from_json(json_data) == original
            assert json.loads(json_data) == original


        def test_unicode_roundtrip_ensure_ascii():
            original = {'name': '中文'}
            json_data = json.dumps(original, ensure_ascii=False).encode()
            assert jiter.from_json(json_data, cache_mode=False) == original
            assert json.loads(json_data) == original


        def test_catch_duplicate_keys():
            assert jiter.from_json(b'{"foo": 1, "foo": 2}') == {'foo': 2}

            with pytest.raises(
                ValueError, match='Detected duplicate key "foo" at line 1 column 18'
            ):
                jiter.from_json(b'{"foo": 1, "foo": 2}', catch_duplicate_keys=True)

            with pytest.raises(
                ValueError, match='Detected duplicate key "foo" at line 1 column 28'
            ):
                jiter.from_json(b'{"foo": 1, "bar": 2, "foo": 2}', catch_duplicate_keys=True)


        def test_against_json():
            for data in JITER_BENCH_DATAS:
                assert jiter.from_json(data) == json.loads(data)


        # def test_multithreaded_parsing():
        #     """Basic sanity check that running a parse in multiple threads is fine."""
        #     expected_datas = [json.loads(data) for data in JITER_BENCH_DATAS]

        #     def assert_jiter_ok(data: bytes, expected: Any) -> bool:
        #         return jiter.from_json(data) == expected

        #     with ThreadPoolExecutor(8) as pool:
        #         results = []
        #         for _ in range(1000):
        #             for data, expected_result in zip(JITER_BENCH_DATAS, expected_datas):
        #                 results.append(pool.submit(assert_jiter_ok, data, expected_result))

        #         for result in results:
        #             assert result.result()
        
        #execute tests
        test_python_parse_numeric()
        test_python_parse_other_no_cache()
        test_python_disallow_nan()
        test_error()
        test_recursion_limit()
        test_recursion_limit_incr()
        test_extracted_value_error()
        test_partial_array()
        test_partial_array_trailing_strings()
        test_partial_array_first()
        test_partial_object()
        test_partial_object_string()
        test_partial_object_string_trailing_strings()
        test_partial_nested()
        test_partial_error()
        test_python_cache_usage_all()
        test_python_cache_usage_keys()
        test_python_cache_usage_none()
        test_use_tape()
        test_unicode()
        test_unicode_cache()
        test_json_float()
        test_json_float_scientific()
        test_json_float_invalid()
        test_lossless_floats()
        test_decimal_floats()
        test_unicode_roundtrip()
        test_unicode_roundtrip_ensure_ascii()
        test_catch_duplicate_keys()
        test_against_json()
