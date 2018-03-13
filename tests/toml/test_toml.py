from poetry.toml import loads

from poetry.toml.prettify.errors import TOMLError


def test_loading_toml_without_trailing_newline():
    toml_text = '[main]\nname = "azmy"'
    toml = loads(toml_text)

    assert toml['main']['name'] == 'azmy'


def test_array_edge_cases():

    # Parsing an empty array value
    toml_text = """[section]
key = []"""

    toml = loads(toml_text)

    assert 'section' in toml
    assert len(toml['section']['key']) == 0


def test_loading_an_empty_toml_source():

    toml_text = ''

    loads(toml_text)

    # Should not fail


def test_parsing_section_with_indentation_and_comment_lines():
    toml = """[main]
listen = ":8966"
redis_host =  "localhost:6379"
redis_password = ""

[influxdb]
host = "localhost:8086"
db   = "agentcontroller"
user = "ac"
password = "acctrl"

[handlers]
binary = "python2.7"
cwd = "./handlers"
    [handlers.env]
    PYTHONPATH = "/opt/jumpscale7/lib:../client"
    SYNCTHING_URL = "http://localhost:8384/"
    SYNCTHING_SHARED_FOLDER_ID = "jumpscripts"
    #SYNCTHING_API_KEY = ""
    REDIS_ADDRESS = "localhost"
    REDIS_PORT = "6379"
    #REDIS_PASSWORD = ""
"""

    f = loads(toml)

    assert f['handlers']['env']['REDIS_ADDRESS'] == 'localhost'
    assert 'REDIS_PASSWORD' not in f['handlers']['env']

    f['handlers']['env']['REDIS_PASSWORD'] = 'MYPASSWORD'

    expected = """[main]
listen = ":8966"
redis_host =  "localhost:6379"
redis_password = ""

[influxdb]
host = "localhost:8086"
db   = "agentcontroller"
user = "ac"
password = "acctrl"

[handlers]
binary = "python2.7"
cwd = "./handlers"
    [handlers.env]
    PYTHONPATH = "/opt/jumpscale7/lib:../client"
    SYNCTHING_URL = "http://localhost:8384/"
    SYNCTHING_SHARED_FOLDER_ID = "jumpscripts"
    #SYNCTHING_API_KEY = ""
    REDIS_ADDRESS = "localhost"
    REDIS_PORT = "6379"
    REDIS_PASSWORD = "MYPASSWORD"
    #REDIS_PASSWORD = ""
"""
    assert expected == f.dumps()


def test_loading_complex_file_1():

    toml = """
[main]
gid = 1
nid = 10
max_jobs = 100
message_id_file = "./.mid"
history_file = "./.history"
agent_controllers = ["http://localhost:8966/"]

[cmds]
    [cmds.execute_js_py]
    binary = "python2.7"
    cwd = "./jumpscripts"
    script = "{domain}/{name}.py"

    [cmds.sync]
    #syncthing extension
    binary = "python2.7"
    cwd = "./extensions/sync"
    script = "{name}.py"
    [cmds.sync.env]
    PYTHONPATH = "../"
    JUMPSCRIPTS_HOME = "../../jumpscripts"
    SYNCTHING_URL = "http://localhost:8384"

[channel]
cmds = [0] # long polling from agent 0

[logging]
    [logging.db]
    type = "DB"
    log_dir = "./logs"
    levels = [2, 4, 7, 8, 9]  # (all error messages) empty for all

    [logging.ac]
    type = "AC"
    flush_int = 300 # seconds (5min)
    batch_size = 1000 # max batch size, force flush if reached this count.
    agent_controllers = [] # to all agents
    levels = [2, 4, 7, 8, 9]  # (all error messages) empty for all

    [logging.console]
    type = "console"
    levels = [2, 4, 7, 8, 9]

[stats]
interval = 60 # seconds
agent_controllers = []
"""

    loads(toml)


def test_weird_edge_case_1():
    toml_text = """l = "t"
creativity = "on vacation"
"""

    f = loads(toml_text)
    assert f['']['l'] == 't'


def test_accessing_deeply_nested_dicts():
    t = """[cmds]
    [cmds.sync]
    #syncthing extension
    binary = "python2.7"
    cwd = "./extensions/sync"
    script = "{name}.py"
        [cmds.sync.env]
        PYTHONPATH = "../"
        JUMPSCRIPTS_HOME = "../../jumpscripts"
        SYNCTHING_URL = "http://localhost:8384"
"""

    f = loads(t)

    assert f['cmds']['sync']['env']['SYNCTHING_URL'] == 'http://localhost:8384'

    f['cmds']['sync']['env']['SYNCTHING_URL'] = 'Nowhere'

    expected_toml = """[cmds]
    [cmds.sync]
    #syncthing extension
    binary = "python2.7"
    cwd = "./extensions/sync"
    script = "{name}.py"
        [cmds.sync.env]
        PYTHONPATH = "../"
        JUMPSCRIPTS_HOME = "../../jumpscripts"
        SYNCTHING_URL = "Nowhere"
"""

    assert expected_toml == f.dumps()


def test_table_with_pound_in_title():
    toml = """["key#group"]
answer = 42"""

    parsed = loads(toml)

    assert parsed.primitive['key#group']['answer'] == 42


def test_fails_to_parse_bad_escape_characters():
    toml = r"""
invalid-escape = r"This string has a bad \a escape character."
"""
    try:
        loads(toml)
        assert False, "Should raise an exception before getting here"
    except TOMLError:
        pass


def test_parsing_multiline_strings_correctly():

    toml = r'''multiline_empty_one = """"""
multiline_empty_two = """
"""
multiline_empty_three = """\
    """
multiline_empty_four = """\
   \
   \
   """

equivalent_one = "The quick brown fox jumps over the lazy dog."
equivalent_two = """
The quick brown \


  fox jumps over \
    the lazy dog."""

equivalent_three = """\
       The quick brown \
       fox jumps over \
       the lazy dog.\
       """
'''

    parsed = loads(toml)

    assert parsed['']['multiline_empty_one'] == parsed['']['multiline_empty_two'] == \
           parsed['']['multiline_empty_three'] == parsed['']['multiline_empty_four']


def test_unicode_string_literals():
    toml = u'answer = "δ"\n'
    parsed = loads(toml)
    assert parsed['']['answer'] == u"δ"


def test_one_entry_array_of_tables():
    t = '''[[people]]
first_name = "Bruce"
last_name = "Springsteen"
'''

    parsed = loads(t)

    assert parsed['people'][0]['first_name'] == 'Bruce'
    assert parsed['people'][0]['last_name'] == 'Springsteen'


def non_empty(iterable):
    return tuple(filter(bool, iterable))

