
from crossplane.pythonic import protobuf


def test_map():
    value = protobuf.Map(a=1, b=2)
    assert len(value) == 2
    assert value.a == 1
    assert value['a'] == 1
    assert value.b == 2
    value.c = 3
    assert len(value) == 3
    assert value.c == 3

def test_list():
    value = protobuf.List(1, 2)
    assert len(value) == 2
    assert value[0] == 1
    assert value[1] == 2
    value[2] = 3
    assert len(value) == 3
    assert value[2] == 3

def test_unkown():
    value = protobuf.Unknown()
    assert not value
    assert value._isUnknown
    value.a = 1
    assert value
    assert not value._isUnknown
    assert value._isMap
    value = protobuf.Unknown()
    assert not value
    assert value._isUnknown
    value[0] = 1
    assert value
    assert not value._isUnknown
    assert value._isList

def test_yaml():
    value = protobuf.Yaml('''
a: 1
b: 2
''')
    assert isinstance(value, protobuf.Values)
    assert value._isMap
    assert len(value) == 2
    value = protobuf.Yaml('''
- 1
- 2
''')
    assert isinstance(value, protobuf.Values)
    assert value._isList
    assert len(value) == 2
    value = protobuf.Yaml('test')
    assert isinstance(value, str)
    value = protobuf.Yaml('1')
    assert isinstance(value, int)
    value = protobuf.Yaml('1.2')
    assert isinstance(value, float)

def test_json():
    value = protobuf.Json('''
{
    "a": 1,
    "b": 2
}
''')
    assert isinstance(value, protobuf.Values)
    assert value._isMap
    assert len(value) == 2
    value = protobuf.Json('''
[
    1,
    2
]
''')
    assert isinstance(value, protobuf.Values)
    assert value._isList
    assert len(value) == 2
    value = protobuf.Json('"test"')
    assert isinstance(value, str)
    value = protobuf.Json('1')
    assert isinstance(value, int)
    value = protobuf.Json('1.2')
    assert isinstance(value, float)

def test_values_map():
    values = protobuf.Map(
        map=protobuf.Map(),
        map2={},
        list=protobuf.List(),
        list2=[],
        unknown=protobuf.Unknown(),
        none=None,
        str='test',
        int=1,
        float=1.1,
        bool=True,
    )
    assert isinstance(values.map, protobuf.Values)
    assert values.map._isMap
    assert isinstance(values.map2, protobuf.Values)
    assert values.map2._isMap
    assert isinstance(values.list, protobuf.Values)
    assert values.list._isList
    assert isinstance(values.list2, protobuf.Values)
    assert values.list2._isList
    assert isinstance(values.unknown, protobuf.Values)
    assert values.unknown._isUnknown
    assert values.none is None
    assert isinstance(values.str, str)
    assert values.str == 'test'
    assert isinstance(values.int, int)
    assert values.int == 1
    assert isinstance(values.float, float)
    assert values.float == 1.1
    assert isinstance(values.bool, bool)
    assert values.bool is True
    assert isinstance(values.placeholder, protobuf.Values)
    assert values.placeholder._isUnknown
    assert 'map' in values
    assert 'nope' not in values
    assert values == values
    assert hash(values) == hash(values)
    assert values._hasUnknowns

def test_values_list():
    values = protobuf.List(
        protobuf.Map(),     # 0
        {},                 # 1
        protobuf.List(),    # 2
        [],                 # 3
        protobuf.Unknown(), # 4
        None,               # 5
        'test',             # 6
        1,                  # 7
        1.1,                # 8
        True,               # 9
    )
    assert isinstance(values[0], protobuf.Values)
    assert values[0]._isMap
    assert isinstance(values[1], protobuf.Values)
    assert values[1]._isMap
    assert isinstance(values[2], protobuf.Values)
    assert values[2]._isList
    assert isinstance(values[3], protobuf.Values)
    assert values[3]._isList
    assert isinstance(values[4], protobuf.Values)
    assert values[4]._isUnknown
    assert values[5] is None
    assert isinstance(values[6], str)
    assert values[6] == 'test'
    assert isinstance(values[7], int)
    assert values[7] == 1
    assert isinstance(values[8], float)
    assert values[8] == 1.1
    assert isinstance(values[9], bool)
    assert values[9] is True
    assert isinstance(values[10], protobuf.Values)
    assert values[10]._isUnknown
    assert 'test' in values
    assert 'nope' not in values
    assert protobuf.Unknown() in values
    assert values == values
    assert hash(values) == hash(values)
    assert values._hasUnknowns

def test_create_child():
    map = protobuf.Unknown()
    list = protobuf.Unknown()
    map.a.b = 'c'
    assert 'b' in map.a
    assert map.a.b == 'c'
    del map.a.b
    assert 'b' not in map.a
    assert not map._hasUnknowns
    map.a.b = protobuf.Unknown()
    assert map._hasUnknowns
    list[0][0] = 'c'
    assert 'c' in list[0]
    assert list[0][0] == 'c'
    del list[0][0]
    assert 'c' not in list[0]
    assert not list._hasUnknowns
    list[0][0] = protobuf.Unknown()
    assert list._hasUnknowns
